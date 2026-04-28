# EXPLAINER.md — Playto Payout Engine

## 1. The Ledger — Balance Calculation Query

The query:

    balance_data = merchant.ledger_entries.aggregate(total=Sum('amount'))
    available_balance = balance_data['total'] or 0

Why I modeled credits and debits this way:

I used an append-only ledger pattern instead of storing a mutable balance column. Every credit is stored as a positive integer and every debit as a negative integer in the amount field. Balance is always derived as SUM(amount) at the database level — never Python arithmetic on fetched rows.

This means no race conditions on balance updates, full audit trail, and mathematical correctness. BigIntegerField stores values in paise to avoid float precision errors.

## 2. The Lock — Preventing Concurrent Overdraw

The exact code:

    with transaction.atomic():
        merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)
        balance_data = merchant_locked.ledger_entries.aggregate(total=Sum('amount'))
        available_balance = balance_data['total'] or 0
        held = merchant_locked.payouts.filter(
            status__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(total=Sum('amount_paise'))['total'] or 0
        spendable = available_balance - held
        if amount_paise > spendable:
            return Response({'error': 'Insufficient balance'}, status=400)
        payout = Payout.objects.create(...)

Database primitive: SELECT FOR UPDATE

select_for_update() acquires a row-level exclusive lock on the merchant row. Any other transaction attempting SELECT FOR UPDATE on the same merchant blocks and waits. This eliminates the check-then-act race condition where two simultaneous requests could both read the same balance and both pass the check.

## 3. The Idempotency

How the system detects a seen key:

    existing = Payout.objects.filter(
        merchant=merchant,
        idempotency_key=idempotency_key
    ).first()
    if existing:
        return Response(PayoutSerializer(existing).data, status=200)

What happens if the first request is still in-flight:

If the first request is still inside transaction.atomic(), the second finds no existing payout and tries to create one. The unique_together constraint on (merchant, idempotency_key) raises IntegrityError which we catch and return the existing payout. Defense in depth.

## 4. The State Machine — Blocking Illegal Transitions

    VALID_TRANSITIONS = {
        PENDING: [PROCESSING],
        PROCESSING: [COMPLETED, FAILED],
        COMPLETED: [],
        FAILED: [],
    }

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

COMPLETED and FAILED map to empty lists — no transitions allowed from terminal states. Every state change checks can_transition_to() first. Failed payouts atomically return funds in the same transaction as the status change.

## 5. The AI Audit — Where I Caught Wrong Code

What AI gave me (wrong):

When generating the concurrency test, AI used the same idempotency key for both threads. This meant both requests were the same idempotent request — the second always returned 200, not 400. The test was testing idempotency, not concurrency.

What I caught:

Both threads sharing one key means only one payout is ever attempted. It proved nothing about race conditions.

What I replaced it with:

Each thread uses a distinct idempotency key (concurrent-key-1 and concurrent-key-2). Now both requests genuinely compete for the same balance, and exactly one succeeds while the other correctly fails with insufficient funds.