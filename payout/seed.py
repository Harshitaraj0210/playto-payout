import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playto.settings')
django.setup()

from payout.models import Merchant, LedgerEntry

def seed():
    print("Seeding merchants...")

    merchants_data = [
        {
            'name': 'Rahul Designs',
            'email': 'rahul@designs.com',
            'bank_account': 'HDFC0001234567',
            'credits': [50000, 75000, 120000],  # in paise
        },
        {
            'name': 'Priya Freelance',
            'email': 'priya@freelance.com',
            'bank_account': 'ICICI0009876543',
            'credits': [200000, 150000],
        },
        {
            'name': 'TechFlow Agency',
            'email': 'techflow@agency.com',
            'bank_account': 'AXIS0005556667',
            'credits': [500000, 300000, 200000],
        },
    ]

    for data in merchants_data:
        merchant, created = Merchant.objects.get_or_create(
            email=data['email'],
            defaults={
                'name': data['name'],
                'bank_account': data['bank_account'],
            }
        )
        if created:
            print(f"Created merchant: {merchant.name}")
            for amount in data['credits']:
                LedgerEntry.objects.create(
                    merchant=merchant,
                    amount=amount,
                    entry_type=LedgerEntry.CREDIT,
                    description='Initial customer payment',
                )
            print(f"  Balance: {sum(data['credits'])} paise = ₹{sum(data['credits'])/100:.2f}")
        else:
            print(f"Merchant already exists: {merchant.name}")

    print("\nDone! Merchants seeded.")

if __name__ == '__main__':
    seed()