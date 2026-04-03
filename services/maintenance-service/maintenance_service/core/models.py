"""maintenance_service/core/models.py"""
import uuid
from django.db import models

MAINTENANCE_TYPE = [
    ("PREVENTIVE","Preventive"), ("CORRECTIVE","Corrective"),
    ("BATTERY_SWAP","Battery Swap"), ("TYRE_CHANGE","Tyre Change"),
    ("BRAKE_SERVICE","Brake Service"), ("ELECTRICAL","Electrical"),
    ("BODY_REPAIR","Body Repair"), ("INSPECTION","Inspection"),
]
MAINTENANCE_STATUS = [
    ("SCHEDULED","Scheduled"), ("IN_PROGRESS","In Progress"),
    ("COMPLETED","Completed"), ("CANCELLED","Cancelled"),
]
ALERT_SEVERITY = [("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("CRITICAL","Critical")]

# Unmanaged stubs
class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True)
    registration_number = models.CharField(max_length=20)
    hub_id = models.UUIDField(null=True)
    status = models.CharField(max_length=20)
    current_odometer_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    battery_health_pct  = models.DecimalField(max_digits=5,  decimal_places=2, null=True)
    insurance_expiry    = models.DateField(null=True)
    puc_expiry          = models.DateField(null=True)
    fitness_expiry      = models.DateField(null=True)
    next_service_km     = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    next_service_date   = models.DateField(null=True)
    class Meta:
        db_table = "vehicles"
        managed  = False

class AdminUser(models.Model):
    id = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    class Meta:
        db_table = "admin_users"
        managed  = False

class MaintenanceLog(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle          = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="maintenance_logs")
    hub_id           = models.UUIDField()
    maintenance_type = models.CharField(max_length=30, choices=MAINTENANCE_TYPE)
    status           = models.CharField(max_length=20, choices=MAINTENANCE_STATUS, default="SCHEDULED")
    scheduled_date   = models.DateField(null=True, blank=True)
    started_at       = models.DateTimeField(null=True, blank=True)
    completed_at     = models.DateTimeField(null=True, blank=True)
    downtime_hours   = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    description      = models.TextField(null=True, blank=True)
    parts_replaced   = models.JSONField(null=True, blank=True)  # [{part,qty,cost}]
    labour_cost      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parts_cost       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    odometer_at_service = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_service_km  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    performed_by_vendor = models.CharField(max_length=200, null=True, blank=True)
    invoice_url      = models.TextField(null=True, blank=True)
    logged_by_id     = models.UUIDField()
    notes            = models.TextField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_logs"
        indexes  = [
            models.Index(fields=["vehicle_id", "-created_at"]),
            models.Index(fields=["hub_id"]),
            models.Index(fields=["status", "scheduled_date"]),
        ]

    @property
    def total_cost(self):
        return float(self.labour_cost) + float(self.parts_cost)

    def __str__(self):
        return f"{self.maintenance_type} — {self.vehicle_id} [{self.status}]"


class MaintenanceAlert(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle      = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_alerts")
    alert_type   = models.CharField(max_length=100)
    severity     = models.CharField(max_length=20, choices=ALERT_SEVERITY, default="MEDIUM")
    message      = models.TextField()
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by_id = models.UUIDField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_alerts"
        indexes  = [
            models.Index(fields=["vehicle_id","is_acknowledged"]),
            models.Index(fields=["severity",  "created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.alert_type} — vehicle {self.vehicle_id}"
