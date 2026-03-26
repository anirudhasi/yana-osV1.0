"""
fleet_service/core/services.py

All fleet business logic:
  - Vehicle CRUD + status machine
  - Allotment engine (allocate + return)
  - GPS telemetry update
  - Compliance checks
  - Alert generation
"""
import logging
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone

from .models import (
    Vehicle, VehicleAllotment, VehicleGPSTelemetry,
    FleetHub, MaintenanceAlert, VehicleStatusAudit,
)
from .exceptions import AllotmentConflictError, VehicleStatusError, ReturnError

logger = logging.getLogger(__name__)


# ─── Status audit helper ──────────────────────────────────────

def _log_status_change(vehicle: Vehicle, old: str, new: str,
                        changed_by_id=None, reason: str = None):
    VehicleStatusAudit.objects.create(
        vehicle=vehicle,
        old_status=old,
        new_status=new,
        changed_by_id=changed_by_id,
        reason=reason,
    )


# ─── Hub CRUD ─────────────────────────────────────────────────

@transaction.atomic
def create_hub(validated_data: dict, admin_id: str) -> FleetHub:
    from .models import City
    city_id = validated_data.get("city_id")
    try:
        city = City.objects.get(id=city_id, is_active=True)
    except City.DoesNotExist:
        raise VehicleStatusError(f"City {city_id} not found or inactive.")

    hub = FleetHub.objects.create(
        city=city,
        name=validated_data["name"],
        address=validated_data["address"],
        latitude=validated_data.get("latitude"),
        longitude=validated_data.get("longitude"),
        capacity=validated_data.get("capacity", 0),
        manager_id=admin_id,
    )
    logger.info("Hub created: %s (%s)", hub.name, hub.id)
    return hub


# ─── Vehicle CRUD ─────────────────────────────────────────────

@transaction.atomic
def create_vehicle(validated_data: dict, admin_id: str) -> Vehicle:
    hub_id = validated_data.pop("hub_id", None)
    try:
        hub = FleetHub.objects.get(id=hub_id, is_active=True)
    except FleetHub.DoesNotExist:
        raise VehicleStatusError(f"Hub {hub_id} not found or inactive.")

    # Check hub capacity
    current_count = hub.vehicles.filter(deleted_at__isnull=True).count()
    if hub.capacity > 0 and current_count >= hub.capacity:
        raise VehicleStatusError(
            f"Hub '{hub.name}' is at full capacity ({hub.capacity} vehicles)."
        )

    vehicle = Vehicle.objects.create(hub=hub, **validated_data)
    _log_status_change(vehicle, None, "AVAILABLE",
                        changed_by_id=admin_id, reason="Vehicle registered")
    logger.info("Vehicle created: %s at hub %s", vehicle.registration_number, hub.name)
    return vehicle


@transaction.atomic
def update_vehicle(vehicle: Vehicle, validated_data: dict, admin_id: str) -> Vehicle:
    hub_id = validated_data.pop("hub_id", None)
    if hub_id and str(hub_id) != str(vehicle.hub_id):
        try:
            new_hub = FleetHub.objects.get(id=hub_id, is_active=True)
        except FleetHub.DoesNotExist:
            raise VehicleStatusError(f"Hub {hub_id} not found.")
        if vehicle.status == "ALLOCATED":
            raise VehicleStatusError("Cannot transfer hub while vehicle is allocated.")
        vehicle.hub = new_hub

    for field, value in validated_data.items():
        setattr(vehicle, field, value)

    vehicle.save()
    return vehicle


@transaction.atomic
def change_vehicle_status(vehicle: Vehicle, new_status: str,
                           admin_id: str, reason: str = None) -> Vehicle:
    valid_transitions = {
        "AVAILABLE":   ["ALLOCATED", "MAINTENANCE", "RETIRED", "LOST"],
        "ALLOCATED":   ["AVAILABLE", "MAINTENANCE"],  # Return handles ALLOCATED→AVAILABLE
        "MAINTENANCE": ["AVAILABLE", "RETIRED"],
        "RETIRED":     [],
        "LOST":        ["AVAILABLE"],
    }
    allowed = valid_transitions.get(vehicle.status, [])
    if new_status not in allowed:
        raise VehicleStatusError(
            f"Cannot change status from '{vehicle.status}' to '{new_status}'."
        )
    old = vehicle.status
    vehicle.status = new_status
    vehicle.save(update_fields=["status", "updated_at"])
    _log_status_change(vehicle, old, new_status, changed_by_id=admin_id, reason=reason)
    return vehicle


@transaction.atomic
def soft_delete_vehicle(vehicle: Vehicle, admin_id: str) -> Vehicle:
    if vehicle.status == "ALLOCATED":
        raise VehicleStatusError("Cannot delete an allocated vehicle. Return it first.")
    vehicle.deleted_at = timezone.now()
    vehicle.status     = "RETIRED"
    vehicle.save(update_fields=["deleted_at", "status", "updated_at"])
    _log_status_change(vehicle, vehicle.status, "RETIRED",
                        changed_by_id=admin_id, reason="Soft deleted")
    return vehicle


# ─── Allotment Engine ─────────────────────────────────────────

@transaction.atomic
def allocate_vehicle(validated_data: dict, admin_id: str) -> VehicleAllotment:
    """
    The core allotment engine.
    Checks:
      1. Vehicle is AVAILABLE
      2. Rider has no active allotment
      3. Unique constraints enforced
    Then creates allotment and marks vehicle ALLOCATED.
    """
    rider_id   = validated_data["rider_id"]
    vehicle_id = validated_data["vehicle_id"]

    # Lock vehicle row for update
    try:
        vehicle = Vehicle.objects.select_for_update().get(
            id=vehicle_id, deleted_at__isnull=True
        )
    except Vehicle.DoesNotExist:
        raise VehicleStatusError(f"Vehicle {vehicle_id} not found.")

    if vehicle.status != "AVAILABLE":
        raise VehicleStatusError(
            f"Vehicle {vehicle.registration_number} is not available (current: {vehicle.status})."
        )

    # Check rider doesn't already have an active allotment
    existing = VehicleAllotment.objects.filter(rider_id=rider_id, status="ACTIVE").first()
    if existing:
        raise AllotmentConflictError(
            f"Rider already has active allotment {existing.id} "
            f"(vehicle: {existing.vehicle.registration_number})."
        )

    # Snapshot vehicle condition at allotment time
    allotment = VehicleAllotment.objects.create(
        rider_id=rider_id,
        vehicle=vehicle,
        hub=vehicle.hub,
        allotted_by_id=admin_id,
        expected_return_at=validated_data.get("expected_return_at"),
        odometer_at_allotment=vehicle.current_odometer_km,
        battery_pct_at_allotment=vehicle.battery_level_pct,
        condition_at_allotment=validated_data.get("condition_at_allotment", ""),
        daily_rent_amount=validated_data["daily_rent_amount"],
        security_deposit=validated_data.get("security_deposit", 0),
        status="ACTIVE",
    )

    # Change vehicle status
    old_status     = vehicle.status
    vehicle.status = "ALLOCATED"
    vehicle.save(update_fields=["status", "updated_at"])
    _log_status_change(vehicle, old_status, "ALLOCATED",
                        changed_by_id=admin_id,
                        reason=f"Allotted to rider {rider_id}")

    # Trigger Celery: create rent schedule
    from .tasks import create_rent_schedule_for_allotment
    create_rent_schedule_for_allotment.delay(str(allotment.id))

    logger.info(
        "Vehicle %s allocated to rider %s (allotment %s)",
        vehicle.registration_number, rider_id, allotment.id,
    )
    return allotment


@transaction.atomic
def return_vehicle(allotment_id: str, validated_data: dict, admin_id: str) -> VehicleAllotment:
    """
    Process a vehicle return.
    Updates allotment, vehicle status, and optionally refunds deposit.
    """
    try:
        allotment = VehicleAllotment.objects.select_for_update().select_related("vehicle").get(
            id=allotment_id, status="ACTIVE"
        )
    except VehicleAllotment.DoesNotExist:
        raise ReturnError(f"Active allotment {allotment_id} not found.")

    vehicle    = allotment.vehicle
    return_hub_id = validated_data.get("returned_to_hub_id") or allotment.hub_id

    # Update allotment
    allotment.returned_at           = timezone.now()
    allotment.returned_to_hub_id    = return_hub_id
    allotment.status                = validated_data.get("return_type", "RETURNED")
    allotment.odometer_at_return    = validated_data.get("odometer_at_return")
    allotment.battery_pct_at_return = validated_data.get("battery_pct_at_return")
    allotment.condition_at_return   = validated_data.get("condition_at_return", "")
    allotment.damage_notes          = validated_data.get("damage_notes", "")

    if validated_data.get("refund_deposit", True):
        refund_amt = validated_data.get("deposit_refund_amount") or allotment.security_deposit
        allotment.deposit_refunded     = True
        allotment.deposit_refund_amount = refund_amt

    allotment.save()

    # Update vehicle
    if allotment.odometer_at_return:
        vehicle.current_odometer_km = allotment.odometer_at_return
    if allotment.battery_pct_at_return:
        vehicle.battery_level_pct = allotment.battery_pct_at_return

    # Move vehicle to hub it was returned to
    if str(return_hub_id) != str(vehicle.hub_id):
        try:
            new_hub = FleetHub.objects.get(id=return_hub_id, is_active=True)
            vehicle.hub = new_hub
        except FleetHub.DoesNotExist:
            pass  # keep original hub if return hub not found

    old_status     = vehicle.status
    vehicle.status = "AVAILABLE"
    vehicle.save(update_fields=[
        "status", "current_odometer_km", "battery_level_pct", "hub", "updated_at"
    ])
    _log_status_change(vehicle, old_status, "AVAILABLE",
                        changed_by_id=admin_id,
                        reason=f"Returned — allotment {allotment_id}")

    # Run post-return checks
    _post_return_checks(vehicle, allotment)

    logger.info(
        "Vehicle %s returned (allotment %s, status: %s)",
        vehicle.registration_number, allotment_id, allotment.status,
    )
    return allotment


def _post_return_checks(vehicle: Vehicle, allotment: VehicleAllotment):
    """Generate alerts if needed after return."""
    if vehicle.battery_health_pct and vehicle.battery_health_pct < 70:
        MaintenanceAlert.objects.get_or_create(
            vehicle=vehicle,
            alert_type="BATTERY_DEGRADED",
            is_acknowledged=False,
            defaults={
                "severity": "HIGH",
                "message":  f"Battery health at {vehicle.battery_health_pct}% — below 70% threshold.",
            },
        )
    if vehicle.needs_service:
        MaintenanceAlert.objects.get_or_create(
            vehicle=vehicle,
            alert_type="SERVICE_DUE",
            is_acknowledged=False,
            defaults={
                "severity": "MEDIUM",
                "message":  "Vehicle is due for scheduled service.",
            },
        )
    if allotment.damage_notes:
        MaintenanceAlert.objects.create(
            vehicle=vehicle,
            alert_type="DAMAGE_REPORTED",
            severity="HIGH",
            message=f"Damage reported on return: {allotment.damage_notes}",
        )


# ─── GPS Telemetry ────────────────────────────────────────────

def update_vehicle_telemetry(vehicle_id: str, lat: float, lng: float,
                              speed: Optional[float], battery_pct: Optional[float],
                              odometer: Optional[float]) -> bool:
    """
    Called by FastAPI telemetry sidecar after batching GPS pings.
    Updates the vehicle's live position fields.
    """
    try:
        Vehicle.objects.filter(id=vehicle_id).update(
            last_gps_lat=lat,
            last_gps_lng=lng,
            last_gps_at=timezone.now(),
            battery_level_pct=battery_pct,
            current_odometer_km=odometer or 0,
            updated_at=timezone.now(),
        )
        return True
    except Exception as e:
        logger.error("Failed to update telemetry for vehicle %s: %s", vehicle_id, e)
        return False


# ─── Alert management ─────────────────────────────────────────

@transaction.atomic
def acknowledge_alert(alert_id: str, admin_id: str) -> MaintenanceAlert:
    try:
        alert = MaintenanceAlert.objects.get(id=alert_id)
    except MaintenanceAlert.DoesNotExist:
        raise VehicleStatusError(f"Alert {alert_id} not found.")

    alert.is_acknowledged   = True
    alert.acknowledged_by_id = admin_id
    alert.acknowledged_at   = timezone.now()
    alert.save(update_fields=["is_acknowledged", "acknowledged_by_id", "acknowledged_at"])
    return alert


# ─── Hub utilization summary ──────────────────────────────────

def get_hub_utilization(hub_ids=None):
    """Returns per-hub utilization data for the admin dashboard."""
    from django.db.models import Count, Q
    qs = FleetHub.objects.filter(is_active=True).select_related("city")
    if hub_ids:
        qs = qs.filter(id__in=hub_ids)

    result = []
    for hub in qs:
        vehicles = hub.vehicles.filter(deleted_at__isnull=True)
        total = vehicles.count()
        avail = vehicles.filter(status="AVAILABLE").count()
        alloc = vehicles.filter(status="ALLOCATED").count()
        maint = vehicles.filter(status="MAINTENANCE").count()
        result.append({
            "hub_id":          str(hub.id),
            "hub_name":        hub.name,
            "city_name":       hub.city.name,
            "capacity":        hub.capacity,
            "total_vehicles":  total,
            "available":       avail,
            "allocated":       alloc,
            "maintenance":     maint,
            "utilization_pct": round(alloc * 100 / total, 2) if total else 0.0,
        })
    return result
