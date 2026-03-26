"""fleet_service/core/tasks.py"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_rent_schedule_for_allotment(self, allotment_id: str):
    """
    After vehicle is allocated, notify payments service to create
    a rent schedule. In production this publishes a Redis event;
    payments service consumes it.
    """
    try:
        from fleet_service.core.models import VehicleAllotment
        allotment = VehicleAllotment.objects.get(id=allotment_id)

        # Publish event for payments service
        import json
        from django.core.cache import cache
        event = {
            "event":              "vehicle.allocated",
            "allotment_id":       allotment_id,
            "rider_id":           str(allotment.rider_id),
            "vehicle_id":         str(allotment.vehicle_id),
            "daily_rent_amount":  str(allotment.daily_rent_amount),
            "security_deposit":   str(allotment.security_deposit),
            "allotted_at":        allotment.allotted_at.isoformat(),
        }
        cache.set(f"yana:events:allotment:{allotment_id}", json.dumps(event), timeout=86400)
        logger.info("Published vehicle.allocated event for allotment %s", allotment_id)
        return {"status": "ok", "allotment_id": allotment_id}
    except Exception as exc:
        logger.error("create_rent_schedule failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def check_maintenance_alerts():
    """
    Periodic task (every hour): scan all vehicles and create
    maintenance alerts for:
      - Service due (by date or odometer)
      - Battery health below threshold
      - Insurance/PUC/fitness expiring in 30 days
    """
    import datetime
    from fleet_service.core.models import Vehicle, MaintenanceAlert

    today = timezone.now().date()
    soon  = today + datetime.timedelta(days=30)

    vehicles = Vehicle.objects.filter(
        deleted_at__isnull=True,
        status__in=["AVAILABLE", "ALLOCATED"],
    ).select_related("hub")

    created_count = 0

    for v in vehicles:
        # Service due by date
        if v.next_service_date and v.next_service_date <= today + datetime.timedelta(days=7):
            _, c = MaintenanceAlert.objects.get_or_create(
                vehicle=v, alert_type="SERVICE_DUE_DATE", is_acknowledged=False,
                defaults={"severity": "MEDIUM",
                          "message": f"Scheduled service due on {v.next_service_date}"},
            )
            if c: created_count += 1

        # Service due by odometer
        if v.next_service_km and v.current_odometer_km >= v.next_service_km - 500:
            _, c = MaintenanceAlert.objects.get_or_create(
                vehicle=v, alert_type="SERVICE_DUE_ODOMETER", is_acknowledged=False,
                defaults={"severity": "MEDIUM",
                          "message": f"Service due at {v.next_service_km} km (current: {v.current_odometer_km} km)"},
            )
            if c: created_count += 1

        # Battery health
        if v.battery_health_pct and v.battery_health_pct < 60:
            severity = "CRITICAL" if v.battery_health_pct < 40 else "HIGH"
            _, c = MaintenanceAlert.objects.get_or_create(
                vehicle=v, alert_type="BATTERY_DEGRADED", is_acknowledged=False,
                defaults={"severity": severity,
                          "message": f"Battery health: {v.battery_health_pct}%"},
            )
            if c: created_count += 1

        # Compliance expiry
        for field, label, alert_type in [
            ("insurance_expiry", "Insurance",         "INSURANCE_EXPIRING"),
            ("puc_expiry",       "PUC",               "PUC_EXPIRING"),
            ("fitness_expiry",   "Fitness certificate","FITNESS_EXPIRING"),
        ]:
            val = getattr(v, field)
            if val and val <= soon:
                severity = "CRITICAL" if val <= today else "HIGH"
                _, c = MaintenanceAlert.objects.get_or_create(
                    vehicle=v, alert_type=alert_type, is_acknowledged=False,
                    defaults={"severity": severity,
                              "message": f"{label} expires on {val}"},
                )
                if c: created_count += 1

    logger.info("Maintenance alert check complete — created %d new alerts", created_count)
    return {"vehicles_checked": vehicles.count(), "alerts_created": created_count}


@shared_task
def refresh_hub_utilization_cache():
    """
    Refresh hub utilization data in Redis cache (used by admin dashboard).
    """
    import json
    from django.core.cache import cache
    from fleet_service.core.services import get_hub_utilization

    data = get_hub_utilization()
    cache.set("yana:fleet:hub_utilization", json.dumps(data), timeout=900)
    logger.info("Refreshed hub utilization cache for %d hubs", len(data))
    return {"hubs_refreshed": len(data)}


@shared_task
def flush_gps_batch_to_db(batch: list):
    """
    Bulk-insert GPS telemetry rows from FastAPI sidecar.
    Called by the FastAPI telemetry endpoint after batching.
    """
    from fleet_service.core.models import VehicleGPSTelemetry
    import uuid
    from django.utils.dateparse import parse_datetime

    rows = [
        VehicleGPSTelemetry(
            id=uuid.uuid4(),
            vehicle_id=item["vehicle_id"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            speed_kmh=item.get("speed_kmh"),
            battery_pct=item.get("battery_pct"),
            odometer_km=item.get("odometer_km"),
            recorded_at=parse_datetime(item["recorded_at"]) or timezone.now(),
        )
        for item in batch
    ]
    VehicleGPSTelemetry.objects.bulk_create(rows, ignore_conflicts=True)
    logger.info("Flushed %d GPS rows to DB", len(rows))
    return {"inserted": len(rows)}
