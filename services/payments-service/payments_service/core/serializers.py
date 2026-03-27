"""payments_service/core/serializers.py"""
from decimal import Decimal
from rest_framework import serializers
from .models import RiderWallet, WalletLedger, PaymentTransaction, RentSchedule, UPIMandate


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RiderWallet
        fields = [
            "id", "rider_id", "balance", "total_earned",
            "total_paid", "total_pending_dues",
            "security_deposit_held", "created_at", "updated_at",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    direction_label = serializers.SerializerMethodField()

    class Meta:
        model  = WalletLedger
        fields = [
            "id", "payment_type", "amount", "direction", "direction_label",
            "balance_after", "reference_id", "reference_type",
            "description", "payment_gateway", "gateway_txn_id",
            "accounting_date", "created_at",
        ]

    def get_direction_label(self, obj):
        return "Credit" if obj.direction == "C" else "Debit"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PaymentTransaction
        fields = [
            "id", "rider_id", "amount", "currency", "gateway",
            "gateway_order_id", "gateway_payment_id",
            "gateway_status", "status", "failure_reason",
            "payment_type", "initiated_at", "completed_at",
        ]


class RentScheduleSerializer(serializers.ModelSerializer):
    total_due = serializers.SerializerMethodField()

    class Meta:
        model  = RentSchedule
        fields = [
            "id", "allotment_id", "rider_id", "due_date",
            "amount", "overdue_penalty", "total_due",
            "status", "paid_at", "days_overdue", "created_at",
        ]

    def get_total_due(self, obj):
        return float(obj.amount + obj.overdue_penalty)


class UPIMandateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UPIMandate
        fields = [
            "id", "rider_id", "upi_id", "max_amount",
            "is_active", "activated_at", "revoked_at",
        ]


# ── Request serializers ───────────────────────────────────────

class TopUpInitiateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("10"))

    def validate_amount(self, v):
        if v > Decimal("10000"):
            raise serializers.ValidationError("Maximum top-up amount is ₹10,000.")
        return v


class TopUpConfirmSerializer(serializers.Serializer):
    razorpay_order_id   = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature  = serializers.CharField()


class AdminAdjustmentSerializer(serializers.Serializer):
    amount      = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    direction   = serializers.ChoiceField(choices=["C", "D"])
    description = serializers.CharField(max_length=500)


class IncentiveCreditSerializer(serializers.Serializer):
    amount         = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    description    = serializers.CharField(max_length=500)
    reference_id   = serializers.UUIDField(required=False, allow_null=True)
    reference_type = serializers.ChoiceField(
        choices=["JOB", "BONUS", "REFERRAL", "OTHER"],
        default="OTHER",
    )


class UPISetupSerializer(serializers.Serializer):
    upi_id      = serializers.CharField(max_length=200)
    max_amount  = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("500"))
    rider_name  = serializers.CharField(max_length=200)
    rider_phone = serializers.CharField(max_length=10)

    def validate_upi_id(self, v):
        import re
        if not re.match(r"[\w.\-]+@[\w]+", v):
            raise serializers.ValidationError("Invalid UPI ID format. Example: name@bankname")
        return v.lower()

    def validate_rider_phone(self, v):
        import re
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise serializers.ValidationError("Enter valid 10-digit mobile number.")
        return v


class RentScheduleCreateSerializer(serializers.Serializer):
    allotment_id      = serializers.UUIDField()
    rider_id          = serializers.UUIDField()
    daily_rent_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    security_deposit  = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date        = serializers.DateField()
    days              = serializers.IntegerField(min_value=1, max_value=365, default=30)


class WalletSummarySerializer(serializers.Serializer):
    wallet_id             = serializers.CharField()
    balance               = serializers.FloatField()
    total_earned          = serializers.FloatField()
    total_paid            = serializers.FloatField()
    security_deposit_held = serializers.FloatField()
    pending_dues          = serializers.FloatField()
    credits_last_30d      = serializers.FloatField()
    debits_last_30d       = serializers.FloatField()
    net_last_30d          = serializers.FloatField()
