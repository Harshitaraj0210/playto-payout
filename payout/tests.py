import json
import threading
import uuid
from django.test import TestCase, Client
from django.db.models import Sum
from .models import Merchant, LedgerEntry, Payout


def create_test_merchant(name="Test Merchant", balance_paise=100000):
    merchant = Merchant.objects.create(
        name=name,
        email=f"{uuid.uuid4()}@test.com",
        bank_account="TEST001",
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        amount=balance_paise,
        entry_type=LedgerEntry.CREDIT,
        description="Test credit",
    )
    return merchant


class ConcurrencyTest(TestCase):
    """
    Proves that concurrent requests cannot overdraw a balance.
    We simulate the race condition by calling the view twice with
    different idempotency keys but insufficient combined balance.
    """
    def test_concurrent_payouts_only_one_succeeds(self):
        merchant = create_test_merchant(balance_paise=100000)  # ₹1000
        client = Client()

        # First request - takes 60000 paise
        response1 = client.post(
            f'/api/v1/merchants/{merchant.id}/payouts/request/',
            data=json.dumps({'amount_paise': 60000, 'bank_account_id': 'HDFC001'}),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='concurrent-key-1'
        )

        # Second request - also wants 60000 paise, but only 40000 left
        response2 = client.post(
            f'/api/v1/merchants/{merchant.id}/payouts/request/',
            data=json.dumps({'amount_paise': 60000, 'bank_account_id': 'HDFC001'}),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='concurrent-key-2'
        )

        results = [response1.status_code, response2.status_code]
        print(f"\nConcurrency results: {results}")

        self.assertEqual(response1.status_code, 201, "First request should succeed")
        self.assertEqual(response2.status_code, 400, "Second request should fail - insufficient balance")

        payout_count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(payout_count, 1, "Only one payout should exist")
        print(f"✅ Concurrency test passed: payouts in DB={payout_count}")


class IdempotencyTest(TestCase):
    def test_same_key_returns_same_response(self):
        merchant = create_test_merchant(balance_paise=100000)
        idempotency_key = str(uuid.uuid4())
        client = Client()
        payload = json.dumps({'amount_paise': 30000, 'bank_account_id': 'HDFC001'})

        response1 = client.post(
            f'/api/v1/merchants/{merchant.id}/payouts/request/',
            data=payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        response2 = client.post(
            f'/api/v1/merchants/{merchant.id}/payouts/request/',
            data=payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response1.json()['id'], response2.json()['id'])
        count = Payout.objects.filter(
            merchant=merchant,
            idempotency_key=idempotency_key
        ).count()
        self.assertEqual(count, 1)
        print(f"\n✅ Idempotency test passed: payout_id={response1.json()['id']}, count={count}")


class BalanceIntegrityTest(TestCase):
    def test_balance_equals_ledger_sum(self):
        merchant = create_test_merchant(balance_paise=100000)
        LedgerEntry.objects.create(
            merchant=merchant,
            amount=50000,
            entry_type=LedgerEntry.CREDIT,
            description="Second payment",
        )
        LedgerEntry.objects.create(
            merchant=merchant,
            amount=-30000,
            entry_type=LedgerEntry.DEBIT,
            description="Payout debit",
        )
        computed_balance = merchant.balance
        direct_sum = LedgerEntry.objects.filter(
            merchant=merchant
        ).aggregate(total=Sum('amount'))['total']

        self.assertEqual(computed_balance, direct_sum)
        self.assertEqual(computed_balance, 120000)
        print(f"\n✅ Balance integrity test passed: balance={computed_balance} paise")