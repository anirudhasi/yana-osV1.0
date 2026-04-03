"""
marketplace_service/core/services.py

Business logic:
  - Demand slot lifecycle (publish, cancel, expire)
  - Application flow (apply, shortlist, confirm, reject)
  - Attendance (check-in, check-out)
  - Earnings computation and payout trigger
  - Matching engine integration
"""
import logging
from decimal import Decimal
from typing import List, Optional
from django.db import transaction
from django.utils import timezone

from .models import (
    DemandSlot, DemandApplication, DemandSlotAudit, Client, ClientDarkStore
)
from .exceptions import (
    SlotFullError,
    SlotNotPublishedError,
    AlreadyAppliedError,
    AttendanceError,
    EarningsError,
)

logger = logging.getLogger(__name__)


# ── Audit helper ──────────────────────────────────────────────

def _audit(slot, action, old_status=None, new_status=None, admin_id=None, meta=None):
    DemandSlotAudit.objects.create(
        slot=slot, action=action,
        old_status=old_status, new_status=new_status,
        performed_by_id=admin_id, metadata=meta,
    )


# ── Slot lifecycle ────────────────────────────────────────────

@transaction.atomic
def create_demand_slot(validated_data: dict, admin_id: str) -> DemandSlot:
    slot = DemandSlot.objects.create(
        **validated_data,
        status="DRAFT",
    )
    _audit(slot, "CREATED", new_status="DRAFT", admin_id=admin_id)
    logger.info("Demand slot created: %s", slot.id)
    return slot


@transaction.atomic
def publish_demand_slot(slot: DemandSlot, admin_id: str) -> DemandSlot:
    if slot.status not in ("DRAFT", "CANCELLED"):
        raise SlotNotPublishedError(
            f"Cannot publish slot in status '{slot.status}'."
        )
    old = slot.status
    slot.status       = "PUBLISHED"
    slot.published_at = timezone.now()
    slot.published_by_id = admin_id
    slot.save(update_fields=["status", "published_at", "published_by_id", "updated_at"])
    _audit(slot, "PUBLISHED", old_status=old, new_status="PUBLISHED", admin_id=admin_id)

    # Trigger async matching
    from .tasks import run_matching_for_slot
    run_matching_for_slot.delay(str(slot.id))

    logger.info("Slot %s published by admin %s", slot.id, admin_id)
    return slot


@transaction.atomic
def cancel_demand_slot(slot: DemandSlot, admin_id: str, reason: str = "") -> DemandSlot:
    if slot.status in ("FILLED", "CANCELLED"):
        raise SlotNotPublishedError(f"Cannot cancel slot in status '{slot.status}'.")

    old = slot.status
    slot.status = "CANCELLED"
    slot.save(update_fields=["status", "updated_at"])
    _audit(slot, "CANCELLED", old_status=old, new_status="CANCELLED",
           admin_id=admin_id, meta={"reason": reason})

    # Notify all confirmed riders
    from .tasks import notify_slot_cancelled
    notify_slot_cancelled.delay(str(slot.id), reason)
    return slot


def _refresh_slot_status(slot: DemandSlot):
    """Recalculate slot status from confirmed count."""
    confirmed = DemandApplication.objects.filter(
        demand_slot=slot, status__in=["CONFIRMED", "COMPLETED"]
    ).count()
    slot.riders_confirmed = confirmed
    slot.fill_rate_pct    = Decimal(slot.fill_rate)

    if confirmed >= slot.riders_required:
        slot.status = "FILLED"
    elif confirmed > 0 and slot.status == "PUBLISHED":
        slot.status = "PARTIALLY_FILLED"

    slot.save(update_fields=["riders_confirmed", "fill_rate_pct", "status", "updated_at"])


# ── Application flow ──────────────────────────────────────────

@transaction.atomic
def apply_for_slot(slot_id: str, rider_id: str) -> DemandApplication:
    """
    Rider applies for a demand slot.
    Validates eligibility and slot availability.
    """
    try:
        slot = DemandSlot.objects.select_for_update().get(id=slot_id)
    except DemandSlot.DoesNotExist:
        raise SlotNotPublishedError(f"Slot {slot_id} not found.")

    if slot.status not in ("PUBLISHED", "PARTIALLY_FILLED"):
        raise SlotNotPublishedError(
            f"Slot is not accepting applications (status: {slot.status})."
        )

    if slot.spots_remaining <= 0:
        raise SlotFullError("This slot is fully booked.")

    # Check date — can't apply to past slots
    if slot.shift_date < timezone.now().date():
        raise SlotNotPublishedError("Cannot apply to a past shift.")

    # Duplicate application check
    if DemandApplication.objects.filter(
        demand_slot=slot, rider_id=rider_id,
        status__in=["APPLIED", "SHORTLISTED", "CONFIRMED"],
    ).exists():
        raise AlreadyAppliedError("You have already applied to this slot.")

    application = DemandApplication.objects.create(
        demand_slot = slot,
        rider_id    = rider_id,
        status      = "APPLIED",
    )

    logger.info("Rider %s applied for slot %s", rider_id, slot_id)

    # Trigger async scoring
    from .tasks import score_application
    score_application.delay(str(application.id))

    return application


@transaction.atomic
def decide_application(
    application_id: str,
    action:         str,
    admin_id:       str,
    rejection_reason: str = "",
) -> DemandApplication:
    """
    Admin shortlists, confirms, or rejects a rider application.
    action: CONFIRM | REJECT | SHORTLIST
    """
    try:
        app = DemandApplication.objects.select_for_update().select_related(
            "demand_slot"
        ).get(id=application_id)
    except DemandApplication.DoesNotExist:
        raise EarningsError(f"Application {application_id} not found.")

    slot = app.demand_slot

    if action == "CONFIRM":
        if app.status not in ("APPLIED", "SHORTLISTED"):
            raise EarningsError(f"Cannot confirm application in status '{app.status}'.")

        if slot.spots_remaining <= 0 and app.status != "SHORTLISTED":
            raise SlotFullError("No spots remaining in this slot.")

        app.status        = "CONFIRMED"
        app.confirmed_at  = timezone.now()
        app.confirmed_by_id = admin_id
        app.save(update_fields=["status", "confirmed_at", "confirmed_by_id", "updated_at"])

        # Refresh slot fill counts
        _refresh_slot_status(slot)

        # Notify rider
        from .tasks import notify_application_confirmed
        notify_application_confirmed.delay(str(app.id))

    elif action == "SHORTLIST":
        if app.status != "APPLIED":
            raise EarningsError(f"Can only shortlist APPLIED applications.")
        app.status = "SHORTLISTED"
        app.save(update_fields=["status", "updated_at"])

    elif action == "REJECT":
        if app.status in ("COMPLETED", "WITHDRAWN"):
            raise EarningsError(f"Cannot reject a {app.status} application.")
        app.status           = "REJECTED"
        app.rejection_reason = rejection_reason
        app.save(update_fields=["status", "rejection_reason", "updated_at"])
        _refresh_slot_status(slot)

        from .tasks import notify_application_rejected
        notify_application_rejected.delay(str(app.id), rejection_reason)

    logger.info("Application %s %sed by admin %s", application_id, action, admin_id)
    return app


@transaction.atomic
def withdraw_application(application_id: str, rider_id: str) -> DemandApplication:
    """Rider withdraws their own application."""
    try:
        app = DemandApplication.objects.select_for_update().select_related(
            "demand_slot"
        ).get(id=application_id, rider_id=rider_id)
    except DemandApplication.DoesNotExist:
        raise EarningsError("Application not found.")

    if app.status in ("CONFIRMED", "COMPLETED"):
        raise EarningsError(
            "Cannot withdraw a confirmed application. Contact support."
        )
    old = app.status
    app.status = "WITHDRAWN"
    app.save(update_fields=["status", "updated_at"])
    _refresh_slot_status(app.demand_slot)
    logger.info("Rider %s withdrew application %s (was: %s)", rider_id, application_id, old)
    return app


# ── Attendance ────────────────────────────────────────────────

@transaction.atomic
def record_check_in(
    application_id: str,
    rider_id:       str,
    lat:            Optional[float] = None,
    lng:            Optional[float] = None,
) -> DemandApplication:
    """
    Record rider check-in for a shift.
    Only CONFIRMED applications can check in.
    """
    try:
        app = DemandApplication.objects.select_for_update().select_related(
            "demand_slot"
        ).get(id=application_id, rider_id=rider_id)
    except DemandApplication.DoesNotExist:
        raise AttendanceError("Application not found.")

    if app.status != "CONFIRMED":
        raise AttendanceError(
            f"Cannot check in: application status is '{app.status}' (must be CONFIRMED)."
        )

    if app.check_in_at:
        raise AttendanceError("Already checked in.")

    # Validate check-in is within shift window (±2 hours grace period)
    from datetime import datetime, timedelta
    slot      = app.demand_slot
    shift_dt  = datetime.combine(slot.shift_date, slot.shift_start_time)
    shift_dt  = timezone.make_aware(shift_dt)
    now       = timezone.now()
    grace     = timedelta(hours=2)

    if now < shift_dt - grace:
        raise AttendanceError(
            f"Too early to check in. Shift starts at {slot.shift_start_time}."
        )

    app.check_in_at  = now
    app.check_in_lat = lat
    app.check_in_lng = lng
    app.save(update_fields=["check_in_at", "check_in_lat", "check_in_lng", "updated_at"])

    # Update slot shown-up count
    DemandSlot.objects.filter(id=slot.id).update(
        riders_shown_up=slot.riders_shown_up + 1
    )

    logger.info("Check-in: rider %s for application %s", rider_id, application_id)
    return app


@transaction.atomic
def record_check_out(
    application_id:  str,
    rider_id:        str,
    lat:             Optional[float] = None,
    lng:             Optional[float] = None,
    orders_completed: int = 0,
) -> DemandApplication:
    """
    Record rider check-out. Computes hours worked and queues earnings payout.
    """
    try:
        app = DemandApplication.objects.select_for_update().select_related(
            "demand_slot"
        ).get(id=application_id, rider_id=rider_id)
    except DemandApplication.DoesNotExist:
        raise AttendanceError("Application not found.")

    if not app.check_in_at:
        raise AttendanceError("Must check in before checking out.")

    if app.check_out_at:
        raise AttendanceError("Already checked out.")

    now = timezone.now()
    delta_hours = (now - app.check_in_at).total_seconds() / 3600

    app.check_out_at   = now
    app.check_out_lat  = lat
    app.check_out_lng  = lng
    app.orders_completed = orders_completed
    app.hours_worked   = Decimal(str(round(delta_hours, 2)))
    app.status         = "COMPLETED"
    app.save(update_fields=[
        "check_out_at", "check_out_lat", "check_out_lng",
        "orders_completed", "hours_worked", "status", "updated_at",
    ])

    logger.info(
        "Check-out: rider %s, %.2f hrs, %d orders",
        rider_id, delta_hours, orders_completed,
    )

    # Queue earnings payout
    from .tasks import process_earnings_payout
    process_earnings_payout.delay(str(app.id))

    return app


# ── Earnings ──────────────────────────────────────────────────

@transaction.atomic
def process_single_payout(
    application_id:  str,
    override_amount: Optional[Decimal] = None,
    admin_id:        Optional[str]     = None,
) -> DemandApplication:
    """
    Credit the computed earnings to a rider's wallet via payments-service.
    Called by Celery task after check-out.
    """
    try:
        app = DemandApplication.objects.select_for_update().select_related(
            "demand_slot"
        ).get(id=application_id)
    except DemandApplication.DoesNotExist:
        raise EarningsError(f"Application {application_id} not found.")

    if app.earnings_paid_at:
        logger.info("Earnings already paid for application %s", application_id)
        return app

    amount = override_amount or Decimal(str(app.computed_earnings))

    if amount <= 0:
        logger.warning("Zero earnings for application %s — skipping payout", application_id)
        return app

    # Call payments service to credit incentive
    import httpx
    from django.conf import settings

    try:
        resp = httpx.post(
            f"{settings.PAYMENTS_SERVICE_URL}/api/v1/payments/wallets/{app.rider_id}/incentive/",
            json={
                "amount":        str(amount),
                "description":   f"Earnings for shift: {app.demand_slot.title} on {app.demand_slot.shift_date}",
                "reference_id":  str(app.id),
                "reference_type": "JOB",
            },
            headers={"Authorization": f"Bearer {_get_internal_token()}"},
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error("Payments service call failed for application %s: %s", application_id, e)
        # Re-queue — don't mark as paid
        raise EarningsError(f"Payment credit failed: {e}") from e

    app.earnings_credited = amount
    app.earnings_paid_at  = timezone.now()
    app.save(update_fields=["earnings_credited", "earnings_paid_at", "updated_at"])

    logger.info(
        "Earnings ₹%s credited to rider %s for application %s",
        amount, app.rider_id, application_id,
    )
    return app


def _get_internal_token() -> str:
    """
    Generate a short-lived internal service token for payments-service calls.
    Uses the shared JWT secret.
    """
    import jwt, uuid
    from datetime import datetime, timezone as tz, timedelta
    from django.conf import settings

    payload = {
        "user_id":    "marketplace-service",
        "role":       "SUPER_ADMIN",
        "token_type": "admin",
        "type":       "access",
        "iat":        datetime.now(tz=tz.utc),
        "exp":        datetime.now(tz=tz.utc) + timedelta(minutes=5),
        "jti":        str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


# ── Fill rate analytics ───────────────────────────────────────

def get_fill_rate_report(city_id=None, client_id=None, days=7) -> list:
    from datetime import timedelta
    from django.utils import timezone

    qs = DemandSlot.objects.select_related("client", "dark_store").filter(
        shift_date__gte=timezone.now().date() - timedelta(days=days),
    )
    if city_id:
        qs = qs.filter(city_id=city_id)
    if client_id:
        qs = qs.filter(client_id=client_id)

    result = []
    for slot in qs.order_by("-shift_date"):
        shown_up_rate = (
            round(slot.riders_shown_up * 100 / slot.riders_confirmed, 1)
            if slot.riders_confirmed else 0.0
        )
        result.append({
            "slot_id":         str(slot.id),
            "title":           slot.title,
            "shift_date":      str(slot.shift_date),
            "client_name":     slot.client.name,
            "riders_required": slot.riders_required,
            "riders_confirmed": slot.riders_confirmed,
            "riders_shown_up":  slot.riders_shown_up,
            "fill_rate":       slot.fill_rate,
            "show_up_rate":    shown_up_rate,
            "status":          slot.status,
        })
    return result
