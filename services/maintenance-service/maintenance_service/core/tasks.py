"""maintenance_service/core/tasks.py"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def check_service_alerts():
    """Hourly: scan vehicles and generate maintenance alerts."""
    from maintenance_service.core.models import Vehicle, MaintenanceAlert
    import datetime
    today = timezone.now().date()
    soon  = today + datetime.timedelta(days=7)
    vehicles = Vehicle.objects.filter(deleted_at__isnull=True, status__in=["AVAILABLE","ALLOCATED"]) if hasattr(Vehicle, 'deleted_at') else Vehicle.objects.filter(status__in=["AVAILABLE","ALLOCATED"])
    created = 0
    for v in vehicles:
        checks = [
            (v.next_service_date and v.next_service_date <= soon,       "SERVICE_DUE_DATE",     "MEDIUM", f"Service due {v.next_service_date}"),
            (v.battery_health_pct and v.battery_health_pct < 60,        "BATTERY_DEGRADED",     "HIGH",   f"Battery at {v.battery_health_pct}%"),
            (v.insurance_expiry and v.insurance_expiry <= today + datetime.timedelta(days=30), "INSURANCE_EXPIRING", "HIGH", f"Insurance expires {v.insurance_expiry}"),
            (v.puc_expiry and v.puc_expiry <= today + datetime.timedelta(days=30),             "PUC_EXPIRING",       "HIGH", f"PUC expires {v.puc_expiry}"),
        ]
        for condition, alert_type, severity, message in checks:
            if condition:
                _, c = MaintenanceAlert.objects.get_or_create(vehicle=v, alert_type=alert_type, is_acknowledged=False,
                    defaults={"severity": severity, "message": message})
                if c: created += 1
    logger.info("check_service_alerts: created %d alerts", created)
    return {"created": created}

@shared_task
def check_compliance_expiry():
    """Daily: check compliance document expiry."""
    from maintenance_service.core.models import Vehicle, MaintenanceAlert
    import datetime
    today = timezone.now().date()
    for v in Vehicle.objects.all():
        if v.fitness_expiry and v.fitness_expiry <= today + datetime.timedelta(days=30):
            MaintenanceAlert.objects.get_or_create(vehicle=v, alert_type="FITNESS_EXPIRING", is_acknowledged=False,
                defaults={"severity":"CRITICAL" if v.fitness_expiry <= today else "HIGH", "message": f"Fitness cert expires {v.fitness_expiry}"})
