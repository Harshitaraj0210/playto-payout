from rest_framework import serializers
from .models import Merchant, LedgerEntry, Payout


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['id', 'amount', 'entry_type', 'description', 'created_at']


class MerchantSerializer(serializers.ModelSerializer):
    balance = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'bank_account', 'balance', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            'id', 'merchant', 'amount_paise', 'bank_account_id',
            'status', 'idempotency_key', 'failure_reason',
            'attempt_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'failure_reason', 'attempt_count',
            'created_at', 'updated_at'
        ]


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=50)

    def validate_amount_paise(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value