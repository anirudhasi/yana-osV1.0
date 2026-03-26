"""
fleet_service/core/models.py

Owns: cities, fleet_hubs, vehicles, vehicle_allotments,
      vehicle_gps_telemetry, maintenance_alerts

References (unmanaged): riders, admin_users
"""
import uuid
from django.db import models


# ── Enums ─────────────────────────────────────────────────────

VEHICLE_STATUS = [
    ("AVAILABLE",   "Available"),
    ("ALLOCATED",   "Allocated"),
    ("MAINTENANCE", "Maintenance"),
    ("RETIRED",     "Retired"),
    ("LOST",        "Lost"),
]

ALLOTMENT_STATUS = [
    ("ACTIVE",          "Active"),
    ("RETURNED",        "Returned"),
    ("FORCE_RETURNED",  "Force Returned"),
    ("EXPIRED",         "Expired"),
]

ALERT_SEVERITY = [
    ("LOW",      "Low"),
    ("MEDIUM",   "Medium"),
    ("HIGH",     "High"),
    ("CRITICAL", "Critical"),
]


# ── Unmanaged stubs ───────────────────────────────────────────

class AdminUser(models.Model):
    id        = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    email     = models.EmailField()

    class Meta:
        db_table = "admin_users"
        managed  = False


class Rider(models.Model):
    id        = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    phone     = models.CharField(max_length=15)
    status    = models.CharField(max_length=30)

    class Meta:
        db_table = "riders"
        managed  = False


# ── Owned Models ──────────────────────────────────────────────

class City(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name      = models.CharField(max_length=100)
    state     = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table    = "cities"
        verbose_name_plural = "cities"

    def __str__(self):
        return f"{self.name}, {self.state}"


class FleetHub(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city       = models.ForeignKey(City, on_delete=models.PROTECT, related_name="hubs")
    name       = models.CharField(max_length=200)
    address    = models.TextField()
    latitude   = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude  = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    capacity   = models.IntegerField(default=0)
    manager_id = models.UUIDField(null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fleet_hubs"
        indexes  = [models.Index(fields=["city_id"]),
                    models.Index(fields=["is_active"])]

    @property
    def available_count(self):
        return self.vehicles.filter(status="AVAILABLE", deleted_at__isnull=True).count()

    @property
    def allocated_count(self):
        return self.vehicles.filter(status="ALLOCATED", deleted_at__isnull=True).count()

    @property
    def utilization_pct(self):
        total = self.vehicles.filter(deleted_at__isnull=True).count()
        if not total:
            return 0.0
        return round(self.allocated_count * 100 / total, 2)

    def __str__(self):
        return f"{self.name} ({self.city.name})"


class Vehicle(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hub  = models.ForeignKey(FleetHub, on_delete=models.PROTECT, related_name="vehicles")

    # Identity
    registration_number = models.CharField(max_length=20, unique=True)
    chassis_number      = models.CharField(max_length=50, unique=True, null=True, blank=True)
    motor_number        = models.CharField(max_length=50, unique=True, null=True, blank=True)
    make                = models.CharField(max_length=100, null=True, blank=True)
    model               = models.CharField(max_length=100, null=True, blank=True)
    manufacturing_year  = models.IntegerField(null=True, blank=True)
    color               = models.CharField(max_length=50, null=True, blank=True)

    # EV-specific
    battery_capacity_kwh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    battery_health_pct   = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    range_km             = models.IntegerField(null=True, blank=True)
    max_speed_kmh        = models.IntegerField(null=True, blank=True)

    # Live telemetry (updated by FastAPI sidecar)
    current_odometer_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_gps_lat        = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    last_gps_lng        = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    last_gps_at         = models.DateTimeField(null=True, blank=True)
    battery_level_pct   = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_charging         = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=VEHICLE_STATUS, default="AVAILABLE")

    # Financial / compliance
    purchase_price   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date    = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    puc_expiry       = models.DateField(null=True, blank=True)
    fitness_expiry   = models.DateField(null=True, blank=True)

    rc_document_url        = models.TextField(null=True, blank=True)
    insurance_document_url = models.TextField(null=True, blank=True)

    # Servicing
    next_service_km   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vehicles"
        indexes  = [
            models.Index(fields=["hub_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["registration_number"]),
        ]

    def __str__(self):
        return f"{self.registration_number} ({self.make} {self.model}) [{self.status}]"

    @property
    def needs_service(self):
        from django.utils import timezone
        import datetime
        if self.next_service_date and self.next_service_date <= timezone.now().date() + datetime.timedelta(days=7):
            return True
        if self.next_service_km and self.current_odometer_km >= self.next_service_km - 500:
            return True
        return False

    @property
    def compliance_warnings(self):
        from django.utils import timezone
        import datetime
        warnings = []
        today    = timezone.now().date()
        soon     = today + datetime.timedelta(days=30)
        if self.insurance_expiry and self.insurance_expiry <= soon:
            warnings.append("insurance_expiring")
        if self.puc_expiry and self.puc_expiry <= soon:
            warnings.append("puc_expiring")
        if self.fitness_expiry and self.fitness_expiry <= soon:
            warnings.append("fitness_expiring")
        return warnings


class VehicleAllotment(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id   = models.UUIDField()
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="allotments")
    hub        = models.ForeignKey(FleetHub, on_delete=models.PROTECT, related_name="allotments")

    # Timing
    allotted_at         = models.DateTimeField(auto_now_add=True)
    allotted_by_id      = models.UUIDField()
    expected_return_at  = models.DateTimeField(null=True, blank=True)
    returned_at         = models.DateTimeField(null=True, blank=True)
    returned_to_hub_id  = models.UUIDField(null=True, blank=True)

    # Condition snapshot
    odometer_at_allotment      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    odometer_at_return         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    battery_pct_at_allotment   = models.DecimalField(max_digits=5,  decimal_places=2, null=True, blank=True)
    battery_pct_at_return      = models.DecimalField(max_digits=5,  decimal_places=2, null=True, blank=True)
    condition_at_allotment     = models.TextField(null=True, blank=True)
    condition_at_return        = models.TextField(null=True, blank=True)
    damage_notes               = models.TextField(null=True, blank=True)

    # Pricing
    daily_rent_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposit_refunded     = models.BooleanField(default=False)
    deposit_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=ALLOTMENT_STATUS, default="ACTIVE")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicle_allotments"
        indexes  = [
            models.Index(fields=["rider_id"]),
            models.Index(fields=["vehicle_id"]),
            models.Index(fields=["hub_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            # A rider can only have 1 active allotment
            models.UniqueConstraint(
                fields=["rider_id"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_allotment_per_rider",
            ),
            # A vehicle can only be in 1 active allotment
            models.UniqueConstraint(
                fields=["vehicle_id"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_allotment_per_vehicle",
            ),
        ]

    def __str__(self):
        return f"Allotment {self.id} — rider={self.rider_id} vehicle={self.vehicle_id} [{self.status}]"

    @property
    def km_driven(self):
        if self.odometer_at_allotment and self.odometer_at_return:
            return float(self.odometer_at_return - self.odometer_at_allotment)
        return None


class VehicleGPSTelemetry(models.Model):
    """
    High-volume time-series table.
    Written by FastAPI telemetry sidecar (bulk inserts).
    Partitioned by month in production.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="gps_history")
    latitude    = models.DecimalField(max_digits=10, decimal_places=8)
    longitude   = models.DecimalField(max_digits=11, decimal_places=8)
    speed_kmh   = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    battery_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    odometer_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = "vehicle_gps_telemetry"
        indexes  = [
            models.Index(fields=["vehicle_id", "-recorded_at"]),
        ]
        ordering = ["-recorded_at"]


class MaintenanceAlert(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle       = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="alerts")
    alert_type    = models.CharField(max_length=100)
    severity      = models.CharField(max_length=20, choices=ALERT_SEVERITY, default="MEDIUM")
    message       = models.TextField()
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by_id = models.UUIDField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_alerts"
        indexes  = [
            models.Index(fields=["vehicle_id", "is_acknowledged"]),
            models.Index(fields=["severity", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.alert_type} — {self.vehicle}"


class VehicleStatusAudit(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="status_audit")
    old_status  = models.CharField(max_length=20, null=True, blank=True)
    new_status  = models.CharField(max_length=20)
    changed_by_id = models.UUIDField(null=True, blank=True)
    reason      = models.TextField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_status_audit"
        indexes  = [models.Index(fields=["vehicle_id", "-created_at"])]
