"""
payments_service/core/models.py

Owns: rider_wallets, wallet_ledger, payment_transactions, rent_schedule
References (unmanaged): riders, vehicle_allotments
"""
import uuid
from django.db import models


# ── Enums ─────────────────────────────────────────────────────

PAYMENT_TYPE = [
    ("DAILY_RENT",         "Daily Rent"),
    ("SECURITY_DEPOSIT",   "Security Deposit"),
    ("INCENTIVE",          "Incentive"),
    ("PENALTY",            "Penalty"),
    ("REFUND",             "Refund"),
    ("ADJUSTMENT",         "Adjustment"),
    ("WITHDRAWAL",         "Withdrawal"),
    ("TOPUP",              "Top Up"),
    ("DEPOSIT_REFUND",     "Deposit Refund"),
]

TRANSACTION_STATUS = [
    ("PENDING",    "Pending"),
    ("PROCESSING", "Processing"),
    ("SUCCESS",    "Success"),
    ("FAILED",     "Failed"),
    ("REVERSED",   "Reversed"),
]

RENT_STATUS = [
    ("PENDING",  "Pending"),
    ("PAID",     "Paid"),
    ("OVERDUE",  "Overdue"),
    ("WAIVED",   "Waived"),
    ("PARTIAL",  "Partial"),
]

DIRECTION = [
    ("C", "Credit"),
    ("D", "Debit"),
]


# ── Unmanaged stubs ───────────────────────────────────────────

class Rider(models.Model):
    id        = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    phone     = models.CharField(max_length=15)
    status    = models.CharField(max_length=30)

    class Meta:
        db_table = "riders"
        managed  = False


class VehicleAllotment(models.Model):
    id                = models.UUIDField(primary_key=True)
    rider_id          = models.UUIDField()
    vehicle_id        = models.UUIDField()
    daily_rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status            = models.CharField(max_length=20)
    allotted_at       = models.DateTimeField()

    class Meta:
        db_table = "vehicle_allotments"
        managed  = False


# ── Core Models ───────────────────────────────────────────────

class RiderWallet(models.Model):
    """
    One wallet per rider. Uses optimistic locking (version field)
    to prevent concurrent balance corruption.
    """
    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id             = models.UUIDField(unique=True)

    # Running balances (denormalised for fast reads — ledger is source of truth)
    balance              = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earned         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_pending_dues   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    security_deposit_held = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Optimistic locking — incremented on every update
    version              = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rider_wallets"
        indexes  = [models.Index(fields=["rider_id"])]

    def __str__(self):
        return f"Wallet(rider={self.rider_id}, balance=₹{self.balance})"


class WalletLedger(models.Model):
    """
    Immutable double-entry ledger.
    NEVER update or delete rows — append only.
    Every transaction must produce a balanced entry.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet       = models.ForeignKey(RiderWallet, on_delete=models.PROTECT,
                                     related_name="ledger_entries")
    rider_id     = models.UUIDField(db_index=True)

    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPE)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)   # always positive
    direction    = models.CharField(max_length=1, choices=DIRECTION)      # C or D
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)  # snapshot

    # Reference to the business object this entry relates to
    reference_id   = models.UUIDField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, null=True, blank=True)
    description    = models.TextField(null=True, blank=True)

    # Gateway details
    payment_gateway = models.CharField(max_length=50, null=True, blank=True)
    gateway_txn_id  = models.TextField(null=True, blank=True, db_index=True)
    upi_ref_id      = models.TextField(null=True, blank=True)

    # Accounting date (IST date — for financial reporting)
    accounting_date = models.DateField(db_index=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_ledger"
        indexes  = [
            models.Index(fields=["wallet_id", "-created_at"]),
            models.Index(fields=["rider_id",  "-accounting_date"]),
            models.Index(fields=["payment_type", "accounting_date"]),
        ]
        # Ledger entries must never be changed
        # Enforced at service layer — no update() allowed on this model

    def __str__(self):
        sign = "+" if self.direction == "C" else "-"
        return f"₹{sign}{self.amount} ({self.payment_type}) → bal ₹{self.balance_after}"


class PaymentTransaction(models.Model):
    """
    Gateway-level transaction record (Razorpay / UPI).
    One-to-one with a ledger entry on success.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id        = models.UUIDField(db_index=True)
    ledger_entry    = models.OneToOneField(WalletLedger, on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name="transaction")

    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    currency        = models.CharField(max_length=3, default="INR")

    # Gateway fields
    gateway              = models.CharField(max_length=50)   # razorpay, cashfree, upi_autopay, manual
    gateway_order_id     = models.TextField(null=True, blank=True, unique=True)
    gateway_payment_id   = models.TextField(null=True, blank=True)
    gateway_signature    = models.TextField(null=True, blank=True)
    gateway_status       = models.CharField(max_length=50, null=True, blank=True)
    gateway_raw_response = models.JSONField(null=True, blank=True)

    status          = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default="PENDING")
    failure_reason  = models.TextField(null=True, blank=True)
    payment_type    = models.CharField(max_length=30, choices=PAYMENT_TYPE, null=True, blank=True)

    initiated_at    = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_transactions"
        indexes  = [
            models.Index(fields=["rider_id",       "-created_at"]),
            models.Index(fields=["status",          "-created_at"]),
            models.Index(fields=["gateway_order_id"]),
        ]

    def __str__(self):
        return f"Txn({self.gateway}, ₹{self.amount}, {self.status})"


class RentSchedule(models.Model):
    """
    Auto-generated when a vehicle is allocated.
    One row per day of expected rental.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    allotment_id = models.UUIDField(db_index=True)
    rider_id     = models.UUIDField(db_index=True)

    due_date     = models.DateField(db_index=True)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    status       = models.CharField(max_length=20, choices=RENT_STATUS, default="PENDING")

    # Filled in on payment
    paid_ledger  = models.ForeignKey(WalletLedger, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="rent_payments")
    paid_at      = models.DateTimeField(null=True, blank=True)

    # Penalty for late payment
    overdue_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_applied_at = models.DateTimeField(null=True, blank=True)

    # Days overdue
    days_overdue = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rent_schedule"
        indexes  = [
            models.Index(fields=["allotment_id"]),
            models.Index(fields=["rider_id", "due_date"]),
            models.Index(fields=["due_date",  "status"]),
        ]
        ordering = ["due_date"]

    def __str__(self):
        return f"Rent ₹{self.amount} due {self.due_date} [{self.status}]"


class UPIMandate(models.Model):
    """
    UPI AutoPay mandate per rider — used for automatic daily rent collection.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id        = models.UUIDField(unique=True)
    upi_id          = models.CharField(max_length=200)

    razorpay_mandate_id  = models.TextField(null=True, blank=True, unique=True)
    razorpay_customer_id = models.TextField(null=True, blank=True)

    max_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    is_active       = models.BooleanField(default=False)
    activated_at    = models.DateTimeField(null=True, blank=True)
    revoked_at      = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "upi_mandates"
        indexes  = [models.Index(fields=["rider_id"])]

    def __str__(self):
        return f"UPIMandate(rider={self.rider_id}, upi={self.upi_id}, active={self.is_active})"
