"""
marketplace_service/core/models.py

Owns: clients, client_dark_stores, client_contracts,
      demand_slots, demand_applications
References (unmanaged): riders, fleet_hubs, cities
"""
import uuid
from django.db import models


# ── Enums ─────────────────────────────────────────────────────

DEMAND_STATUS = [
    ("DRAFT",            "Draft"),
    ("PUBLISHED",        "Published"),
    ("PARTIALLY_FILLED", "Partially Filled"),
    ("FILLED",           "Filled"),
    ("EXPIRED",          "Expired"),
    ("CANCELLED",        "Cancelled"),
]

APPLICATION_STATUS = [
    ("APPLIED",      "Applied"),
    ("SHORTLISTED",  "Shortlisted"),
    ("CONFIRMED",    "Confirmed"),
    ("REJECTED",     "Rejected"),
    ("WITHDRAWN",    "Withdrawn"),
    ("NO_SHOW",      "No Show"),
    ("COMPLETED",    "Completed"),
]

SHIFT_TYPE = [
    ("MORNING",   "Morning  (06:00–14:00)"),
    ("AFTERNOON", "Afternoon (14:00–22:00)"),
    ("NIGHT",     "Night     (22:00–06:00)"),
    ("CUSTOM",    "Custom"),
]

PAY_STRUCTURE = [
    ("PER_ORDER", "Per Order"),
    ("PER_SHIFT", "Per Shift"),
    ("PER_HOUR",  "Per Hour"),
    ("HYBRID",    "Hybrid"),
]


# ── Unmanaged stubs ───────────────────────────────────────────

class City(models.Model):
    id   = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    class Meta:
        db_table = "cities"
        managed  = False


class FleetHub(models.Model):
    id   = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)
    class Meta:
        db_table = "fleet_hubs"
        managed  = False


class Rider(models.Model):
    id                = models.UUIDField(primary_key=True)
    full_name         = models.CharField(max_length=200)
    phone             = models.CharField(max_length=15)
    status            = models.CharField(max_length=30)
    reliability_score = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    hub_id            = models.UUIDField(null=True)
    city_id           = models.UUIDField(null=True)
    latitude          = models.DecimalField(max_digits=10, decimal_places=8, null=True)
    longitude         = models.DecimalField(max_digits=11, decimal_places=8, null=True)
    class Meta:
        db_table = "riders"
        managed  = False


# ── CRM / Client models ───────────────────────────────────────

class Client(models.Model):
    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                  = models.CharField(max_length=200)
    category              = models.CharField(max_length=100, null=True, blank=True)
    gstin                 = models.CharField(max_length=20,  null=True, blank=True)
    pan                   = models.CharField(max_length=20,  null=True, blank=True)
    website               = models.URLField(null=True,  blank=True)
    primary_contact_name  = models.CharField(max_length=200, null=True, blank=True)
    primary_contact_email = models.EmailField(null=True, blank=True)
    primary_contact_phone = models.CharField(max_length=15,  null=True, blank=True)
    logo_url              = models.TextField(null=True, blank=True)
    is_active             = models.BooleanField(default=True)
    created_by_id         = models.UUIDField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"

    def __str__(self):
        return self.name


class ClientDarkStore(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client    = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="dark_stores")
    city_id   = models.UUIDField()
    hub_id    = models.UUIDField(null=True, blank=True)
    name      = models.CharField(max_length=200)
    address   = models.TextField()
    latitude  = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_dark_stores"
        indexes  = [
            models.Index(fields=["client_id"]),
            models.Index(fields=["city_id"]),
        ]

    def __str__(self):
        return f"{self.client.name} — {self.name}"


class ClientContract(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client         = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="contracts")
    dark_store     = models.ForeignKey(ClientDarkStore, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="contracts")
    contract_start = models.DateField()
    contract_end   = models.DateField(null=True, blank=True)
    pay_per_order  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pay_per_hour   = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pay_per_shift  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    minimum_guarantee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sla_terms      = models.JSONField(null=True, blank=True)
    document_url   = models.TextField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)
    created_by_id  = models.UUIDField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_contracts"

    def __str__(self):
        return f"{self.client.name} contract [{self.contract_start} → {self.contract_end or '∞'}]"


# ── Demand Slots ──────────────────────────────────────────────

class DemandSlot(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client     = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="demand_slots")
    dark_store = models.ForeignKey(ClientDarkStore, on_delete=models.PROTECT,
                                   related_name="demand_slots")
    city_id    = models.UUIDField(db_index=True)

    # Slot identity
    title       = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    shift_type  = models.CharField(max_length=20, choices=SHIFT_TYPE, default="MORNING")

    # Timing
    shift_date       = models.DateField(db_index=True)
    shift_start_time = models.TimeField()
    shift_end_time   = models.TimeField()
    shift_duration_hrs = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    # Requirements
    riders_required  = models.IntegerField()
    riders_confirmed = models.IntegerField(default=0)
    riders_shown_up  = models.IntegerField(default=0)

    # Compensation
    pay_structure    = models.CharField(max_length=20, choices=PAY_STRUCTURE, default="PER_SHIFT")
    pay_per_order    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pay_per_shift    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pay_per_hour     = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    earnings_estimate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    vehicle_required = models.BooleanField(default=True)

    # Targeting / eligibility
    min_reliability_score = models.DecimalField(max_digits=4, decimal_places=2,
                                                 null=True, blank=True)
    required_hub_ids      = models.JSONField(default=list, blank=True)
    badge_required        = models.CharField(max_length=50, null=True, blank=True)
    city_restriction      = models.BooleanField(default=True)

    # Lifecycle
    status       = models.CharField(max_length=20, choices=DEMAND_STATUS, default="DRAFT")
    published_by_id = models.UUIDField(null=True, blank=True)
    published_at    = models.DateTimeField(null=True, blank=True)
    expires_at      = models.DateTimeField(null=True, blank=True)

    # Fill rate (updated by Celery)
    fill_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "demand_slots"
        indexes  = [
            models.Index(fields=["city_id", "shift_date"]),
            models.Index(fields=["status",  "shift_date"]),
            models.Index(fields=["client_id"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.shift_date}] ({self.riders_confirmed}/{self.riders_required})"

    @property
    def spots_remaining(self):
        return max(0, self.riders_required - self.riders_confirmed)

    @property
    def is_full(self):
        return self.riders_confirmed >= self.riders_required

    @property
    def fill_rate(self):
        if not self.riders_required:
            return 0.0
        return round(self.riders_confirmed * 100 / self.riders_required, 1)


class DemandApplication(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demand_slot    = models.ForeignKey(DemandSlot, on_delete=models.CASCADE,
                                       related_name="applications")
    rider_id       = models.UUIDField(db_index=True)

    applied_at     = models.DateTimeField(auto_now_add=True)
    status         = models.CharField(max_length=20, choices=APPLICATION_STATUS, default="APPLIED")
    confirmed_at   = models.DateTimeField(null=True, blank=True)
    confirmed_by_id = models.UUIDField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    no_show_reason   = models.TextField(null=True, blank=True)

    # Matching score (set by matching engine)
    match_score    = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Attendance
    check_in_at    = models.DateTimeField(null=True, blank=True)
    check_in_lat   = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    check_in_lng   = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    check_out_at   = models.DateTimeField(null=True, blank=True)
    check_out_lat  = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    check_out_lng  = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    # Shift performance
    orders_completed  = models.IntegerField(default=0)
    hours_worked      = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    earnings_credited = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    earnings_paid_at  = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "demand_applications"
        unique_together = [["demand_slot", "rider_id"]]
        indexes = [
            models.Index(fields=["demand_slot_id", "status"]),
            models.Index(fields=["rider_id", "applied_at"]),
        ]

    def __str__(self):
        return f"Application(rider={self.rider_id}, slot={self.demand_slot_id}, {self.status})"

    @property
    def computed_earnings(self):
        """Calculate what the rider should earn for this shift."""
        slot = self.demand_slot
        if slot.pay_structure == "PER_ORDER" and self.orders_completed:
            return float(slot.pay_per_order or 0) * self.orders_completed
        elif slot.pay_structure == "PER_SHIFT":
            return float(slot.pay_per_shift or 0)
        elif slot.pay_structure == "PER_HOUR" and self.hours_worked:
            return float(slot.pay_per_hour or 0) * float(self.hours_worked)
        elif slot.pay_structure == "HYBRID":
            base    = float(slot.pay_per_shift or 0)
            orders  = float(slot.pay_per_order or 0) * self.orders_completed
            return base + orders
        return 0.0


class DemandSlotAudit(models.Model):
    """Immutable audit log for demand slot status changes."""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot       = models.ForeignKey(DemandSlot, on_delete=models.CASCADE, related_name="audit_logs")
    action     = models.CharField(max_length=50)
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    performed_by_id = models.UUIDField(null=True, blank=True)
    metadata   = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "demand_slot_audit"
        indexes  = [models.Index(fields=["slot_id", "-created_at"])]
