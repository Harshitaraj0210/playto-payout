from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Merchant, LedgerEntry, Payout
from .serializers import (
    MerchantSerializer, LedgerEntrySerializer,
    PayoutSerializer, PayoutRequestSerializer
)


@api_view(['GET'])
def merchant_list(request):
    merchants = Merchant.objects.all()
    serializer = MerchantSerializer(merchants, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def merchant_detail(request, merchant_id):
    try:
        merchant = Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({'error': 'Merchant not found'}, status=404)

    # Balance from DB aggregation - never Python arithmetic
    balance_data = merchant.ledger_entries.aggregate(total=Sum('amount'))
    available_balance = balance_data['total'] or 0

    # Held balance = sum of pending/processing payouts
    held = merchant.payouts.filter(
        status__in=[Payout.PENDING, Payout.PROCESSING]
    ).aggregate(total=Sum('amount_paise'))['total'] or 0

    recent_entries = merchant.ledger_entries.all()[:10]

    return Response({
        'id': str(merchant.id),
        'name': merchant.name,
        'email': merchant.email,
        'bank_account': merchant.bank_account,
        'available_balance': available_balance,
        'held_balance': held,
        'recent_entries': LedgerEntrySerializer(recent_entries, many=True).data,
    })

@csrf_exempt
@api_view(['POST'])
def request_payout(request, merchant_id):
    # Validate input
    serializer = PayoutRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    idempotency_key = request.headers.get('Idempotency-Key')
    if not idempotency_key:
        return Response(
            {'error': 'Idempotency-Key header is required'},
            status=400
        )

    try:
        merchant = Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({'error': 'Merchant not found'}, status=404)

    amount_paise = serializer.validated_data['amount_paise']
    bank_account_id = serializer.validated_data['bank_account_id']

    # Check for existing payout with same idempotency key
    existing = Payout.objects.filter(
        merchant=merchant,
        idempotency_key=idempotency_key
    ).first()

    if existing:
        return Response(PayoutSerializer(existing).data, status=200)

    # CRITICAL: Use SELECT FOR UPDATE to lock the merchant's ledger
    # This prevents two simultaneous requests from both seeing sufficient balance
    with transaction.atomic():
        # Lock all ledger entries for this merchant
        merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)

        # Calculate balance at DB level inside the lock
        balance_data = merchant_locked.ledger_entries.aggregate(total=Sum('amount'))
        available_balance = balance_data['total'] or 0

        # Calculate held funds
        held = merchant_locked.payouts.filter(
            status__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(total=Sum('amount_paise'))['total'] or 0

        spendable = available_balance - held

        if amount_paise > spendable:
            return Response(
                {
                    'error': 'Insufficient balance',
                    'available': spendable,
                    'requested': amount_paise
                },
                status=400
            )

        # Create payout - idempotency enforced by unique_together at DB level
        try:
            payout = Payout.objects.create(
                merchant=merchant_locked,
                amount_paise=amount_paise,
                bank_account_id=bank_account_id,
                idempotency_key=idempotency_key,
                status=Payout.PENDING,
            )

            # Debit the held amount from ledger
            LedgerEntry.objects.create(
                merchant=merchant_locked,
                amount=-amount_paise,
                entry_type=LedgerEntry.DEBIT,
                description=f'Payout request {payout.id}',
                payout=payout,
            )

        except Exception:
            # Race condition: another request created with same key
            existing = Payout.objects.get(
                merchant=merchant,
                idempotency_key=idempotency_key
            )
            return Response(PayoutSerializer(existing).data, status=200)

    # Queue background processing
    from django_q.tasks import async_task
    async_task('payout.tasks.process_payout', str(payout.id))

    return Response(PayoutSerializer(payout).data, status=201)


@api_view(['GET'])
def payout_list(request, merchant_id):
    try:
        merchant = Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({'error': 'Merchant not found'}, status=404)

    payouts = merchant.payouts.all()
    return Response(PayoutSerializer(payouts, many=True).data)


@api_view(['GET'])
def payout_detail(request, payout_id):
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        return Response({'error': 'Payout not found'}, status=404)
    return Response(PayoutSerializer(payout).data)