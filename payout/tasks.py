import random
import time
from django.db import transaction
from django.utils import timezone
from .models import Payout, LedgerEntry


def process_payout(payout_id: str):
    """
    Background worker that processes a payout through its lifecycle.
    Simulates bank settlement: 70% success, 20% fail, 10% hang.
    """
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        return

    # Only process pending payouts
    if payout.status != Payout.PENDING:
        return

    # Transition to processing
    with transaction.atomic():
        # Re-fetch with lock to prevent race conditions
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if not payout.can_transition_to(Payout.PROCESSING):
            return
        payout.status = Payout.PROCESSING
        payout.attempt_count += 1
        payout.save()

    # Simulate bank API call
    outcome = random.choices(
        ['success', 'fail', 'hang'],
        weights=[70, 20, 10]
    )[0]

    if outcome == 'hang':
        # Simulate a stuck payout - retry logic will handle this
        time.sleep(35)
        return

    if outcome == 'success':
        _complete_payout(payout)
    else:
        _fail_payout(payout, reason='Bank settlement failed')


def _complete_payout(payout):
    """Mark payout as completed. Debit already recorded at request time."""
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout.id)
        if not payout.can_transition_to(Payout.COMPLETED):
            return
        payout.status = Payout.COMPLETED
        payout.save()


def _fail_payout(payout, reason=''):
    """
    Mark payout as failed and ATOMICALLY return funds to merchant balance.
    This is critical: fund return must happen in the same transaction as
    the status change. Never do these separately.
    """
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout.id)
        if not payout.can_transition_to(Payout.FAILED):
            return
        payout.status = Payout.FAILED
        payout.failure_reason = reason
        payout.save()

        # Atomically return funds - credit back to ledger
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            amount=payout.amount_paise,
            entry_type=LedgerEntry.CREDIT,
            description=f'Refund for failed payout {payout.id}',
            payout=payout,
        )


def retry_stuck_payouts():
    """
    Called periodically to retry payouts stuck in processing > 30 seconds.
    Exponential backoff, max 3 attempts.
    """
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(seconds=30)
    stuck_payouts = Payout.objects.filter(
        status=Payout.PROCESSING,
        updated_at__lt=cutoff
    )

    for payout in stuck_payouts:
        if payout.attempt_count >= 3:
            _fail_payout(payout, reason='Max retry attempts exceeded')
        else:
            # Reset to pending for retry with exponential backoff
            with transaction.atomic():
                p = Payout.objects.select_for_update().get(id=payout.id)
                if p.status == Payout.PROCESSING:
                    p.status = Payout.PENDING
                    p.save()
            # Re-queue with backoff delay
            delay = (2 ** payout.attempt_count) * 5
            from django_q.tasks import async_task
            async_task('payout.tasks.process_payout', str(payout.id),
                      q_options={'eta': timezone.now() + timezone.timedelta(seconds=delay)})