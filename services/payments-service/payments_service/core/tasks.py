"""
payments_service/core/tasks.py

Celery beat tasks:
  - Daily rent deduction (runs at midnight IST)
  - Mark overdue schedules (hourly)
  - Process UPI AutoPay mandates (every 6 hours)
  - Consume vehicle.allocated events from Redis
  - Send payment notifications
"""
import logging
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from django.db.models import Count

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def deduct_daily_rent(self):
    """
    Daily beat task: deduct today's rent for all active riders.
    Runs at 00:05 IST every day via Celery beat.
    """
    from payments_service.core.models import RentSchedule
    from payments_service.core.services import deduct_rent_for_rider

    today = timezone.now().date()

    # Get all rider IDs with due rent today
    rider_ids = list(
        RentSchedule.objects.filter(
            due_date  = today,
            status__in = ["PENDING", "OVERDUE"],
        ).values_list("rider_id", flat=True).distinct()
    )

    logger.info("Starting daily rent deduction for %d riders on %s", len(rider_ids), today)

    success_count  = 0
    failed_count   = 0
    skipped_count  = 0

    for rider_id in rider_ids:
        try:
            entry = deduct_rent_for_rider(str(rider_id), today)
            if entry:
                success_count += 1
                # Notify rider of deduction
                notify_rent_deducted.delay(str(rider_id), float(entry.amount), str(today))
            else:
                skipped_count += 1
        except Exception as e:
            failed_count += 1
            logger.error("Rent deduction failed for rider %s: %s", rider_id, e)

    result = {
        "date":     str(today),
        "total":    len(rider_ids),
        "success":  success_count,
        "failed":   failed_count,
        "skipped":  skipped_count,
    }
    logger.info("Daily rent deduction complete: %s", result)
    return result


@shared_task
def mark_overdue_rent_schedules():
    """
    Hourly task: mark past-due schedules as OVERDUE and apply penalty.
    """
    from payments_service.core.models import RentSchedule
    from payments_service.core.services import _apply_overdue_penalty

    today = timezone.now().date()

    overdue_schedules = RentSchedule.objects.filter(
        due_date__lt = today,
        status       = "PENDING",
    )

    count = 0
    for schedule in overdue_schedules:
        _apply_overdue_penalty(schedule)
        count += 1

    logger.info("Marked %d schedules as OVERDUE", count)
    return {"marked_overdue": count}


@shared_task
def process_upi_autopay_mandates():
    """
    Process automatic UPI debit for riders with active mandates.
    Charges daily rent via UPI AutoPay.
    """
    from payments_service.core.models import UPIMandate, RentSchedule
    from payments_service.core.services import deduct_rent_for_rider
    from payments_service.razorpay import client as rzp

    today = timezone.now().date()

    active_mandates = UPIMandate.objects.filter(is_active=True)

    success = 0
    failed  = 0

    for mandate in active_mandates:
        rider_id = str(mandate.rider_id)

        # Check if there's a rent due today
        schedule = RentSchedule.objects.filter(
            rider_id   = rider_id,
            due_date   = today,
            status__in = ["PENDING", "OVERDUE"],
        ).first()

        if not schedule:
            continue

        total_due = schedule.amount + schedule.overdue_penalty

        try:
            # Charge via UPI AutoPay
            result = rzp.charge_upi_autopay(
                mandate_id  = mandate.razorpay_mandate_id,
                amount_inr  = total_due,
                description = f"Yana daily rent {today}",
            )

            if result.get("status") in ("captured", "created"):
                from payments_service.core.ledger import credit
                from payments_service.core.models import PaymentTransaction
                import uuid

                # Record transaction
                txn = PaymentTransaction.objects.create(
                    rider_id           = rider_id,
                    amount             = total_due,
                    gateway            = "upi_autopay",
                    gateway_payment_id = result.get("payment_id"),
                    gateway_status     = result.get("status"),
                    gateway_raw_response = result,
                    status             = "SUCCESS",
                    payment_type       = "DAILY_RENT",
                    completed_at       = timezone.now(),
                )

                # Credit wallet (the deduction already happens in deduct_rent_for_rider)
                entry = deduct_rent_for_rider(rider_id, today)
                if entry:
                    txn.ledger_entry = entry
                    txn.save(update_fields=["ledger_entry"])
                    success += 1

        except Exception as e:
            failed += 1
            logger.error("UPI AutoPay failed for rider %s: %s", rider_id, e)

    logger.info("UPI AutoPay processing: %d success, %d failed", success, failed)
    return {"success": success, "failed": failed}


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def consume_vehicle_allocated_event(self, allotment_id: str):
    """
    Consumed from Redis when fleet-service publishes vehicle.allocated event.
    Creates the rent schedule for the new allotment.
    """
    import json
    from django.core.cache import cache
    from payments_service.core.services import create_rent_schedule
    from datetime import datetime

    event_key = f"yana:events:allotment:{allotment_id}"
    raw       = cache.get(event_key)

    if not raw:
        logger.warning("No event found for allotment %s", allotment_id)
        return

    try:
        event = json.loads(raw)

        allotted_at   = datetime.fromisoformat(event["allotted_at"])
        start_date    = allotted_at.date()

        schedules = create_rent_schedule(
            allotment_id     = allotment_id,
            rider_id         = event["rider_id"],
            daily_rent       = Decimal(event["daily_rent_amount"]),
            start_date       = start_date,
            days             = 30,
            security_deposit = Decimal(event.get("security_deposit", "0")),
        )

        # Clear the event from Redis
        cache.delete(event_key)

        logger.info(
            "Rent schedule created for allotment %s: %d entries",
            allotment_id, len(schedules),
        )
        return {"allotment_id": allotment_id, "schedules_created": len(schedules)}

    except Exception as exc:
        logger.error("Failed to process vehicle.allocated event: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def poll_fleet_events():
    """
    Periodic task: poll Redis for vehicle.allocated events
    and trigger rent schedule creation.
    Runs every 30 seconds.
    """
    from django.core.cache import cache

    # Scan Redis for allotment events
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys("yana:events:allotment:*")
        count = 0
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            allotment_id = key_str.split(":")[-1]
            consume_vehicle_allocated_event.delay(allotment_id)
            count += 1
        if count:
            logger.info("Queued %d vehicle.allocated events for processing", count)
        return {"queued": count}
    except Exception as e:
        logger.error("Event polling failed: %s", e)
        return {"error": str(e)}


# ── Notification stubs ────────────────────────────────────────

@shared_task
def notify_rent_deducted(rider_id: str, amount: float, date: str):
    """Send WhatsApp/Firebase notification for rent deduction."""
    logger.info(
        "[NOTIFY] Rider %s: ₹%.2f rent deducted for %s",
        rider_id, amount, date,
    )


@shared_task
def notify_low_balance(rider_id: str, balance: float):
    """Alert rider when wallet balance drops below ₹200."""
    logger.warning(
        "[NOTIFY] Rider %s: Low balance warning — ₹%.2f remaining",
        rider_id, balance,
    )


@shared_task
def notify_payment_received(rider_id: str, amount: float):
    logger.info("[NOTIFY] Rider %s: Payment of ₹%.2f received", rider_id, amount)


@shared_task
def generate_monthly_statement(rider_id: str, month: str):
    """
    Generate monthly wallet statement (PDF) and send to rider.
    Placeholder — integrate with PDF generation service in Phase 2.
    """
    from payments_service.core.models import WalletLedger
    from django.db.models import Sum, Q
    import calendar
    from datetime import date

    year, mon = map(int, month.split("-"))
    _, last_day = calendar.monthrange(year, mon)
    start = date(year, mon, 1)
    end   = date(year, mon, last_day)

    entries = WalletLedger.objects.filter(
        rider_id=rider_id,
        accounting_date__range=(start, end),
    )
    totals = entries.aggregate(
        credits=Sum("amount", filter=Q(direction="C")),
        debits =Sum("amount", filter=Q(direction="D")),
    )
    logger.info(
        "[STATEMENT] Rider %s for %s: Credits=₹%s Debits=₹%s",
        rider_id, month,
        totals["credits"] or 0,
        totals["debits"]  or 0,
    )
