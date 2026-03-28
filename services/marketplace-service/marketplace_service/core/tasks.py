"""marketplace_service/core/tasks.py"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_matching_for_slot(self, slot_id: str):
    """
    After a slot is published, find matching riders and
    update their application match_score. Does NOT auto-apply
    riders — just pre-computes scores for admin visibility.
    """
    from marketplace_service.core.models import DemandSlot, DemandApplication
    from marketplace_service.matching.engine import (
        DemandSlotSpec, find_matching_riders, load_rider_profiles_for_slot,
    )
    from django.conf import settings

    try:
        slot = DemandSlot.objects.select_related("dark_store").get(id=slot_id)
    except DemandSlot.DoesNotExist:
        logger.error("Slot %s not found for matching", slot_id)
        return

    spec = DemandSlotSpec(
        slot_id          = str(slot.id),
        city_id          = str(slot.city_id),
        dark_store_lat   = float(slot.dark_store.latitude)  if slot.dark_store.latitude  else None,
        dark_store_lng   = float(slot.dark_store.longitude) if slot.dark_store.longitude else None,
        min_reliability  = float(slot.min_reliability_score or 0),
        required_hub_ids = [str(h) for h in (slot.required_hub_ids or [])],
        badge_required   = slot.badge_required,
        riders_required  = slot.riders_required,
        riders_confirmed = slot.riders_confirmed,
        vehicle_required = slot.vehicle_required,
    )

    profiles = load_rider_profiles_for_slot(slot)
    matches  = find_matching_riders(
        spec,
        profiles,
        max_radius_km=settings.MATCH_RADIUS_KM,
        top_n=slot.riders_required * 3,   # 3x buffer
    )

    # Cache match results in Redis for admin dashboard
    import json
    from django.core.cache import cache
    cache.set(
        f"yana:matches:{slot_id}",
        json.dumps([{
            "rider_id":          m.rider_id,
            "full_name":         m.full_name,
            "score":             m.score,
            "distance_km":       m.distance_km,
            "reliability_score": m.reliability_score,
            "total_completions": m.total_completions,
            "score_breakdown":   m.score_breakdown,
        } for m in matches]),
        timeout=3600,
    )

    logger.info(
        "Matching complete for slot %s: %d candidates → %d matches",
        slot_id, len(profiles), len(matches),
    )
    return {"slot_id": slot_id, "matched": len(matches)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def score_application(self, application_id: str):
    """Score a newly submitted application using the matching engine."""
    from marketplace_service.core.models import DemandApplication, DemandSlot
    from marketplace_service.matching.engine import (
        DemandSlotSpec, RiderProfile, _compute_composite_score, _haversine_km,
    )

    try:
        app  = DemandApplication.objects.select_related(
            "demand_slot__dark_store"
        ).get(id=application_id)
        slot = app.demand_slot
    except DemandApplication.DoesNotExist:
        return

    try:
        from marketplace_service.core.models import Rider
        rider = Rider.objects.get(id=app.rider_id)
    except Exception:
        return

    # Compute distance
    if (slot.dark_store.latitude and slot.dark_store.longitude
            and rider.latitude and rider.longitude):
        dist = _haversine_km(
            float(rider.latitude), float(rider.longitude),
            float(slot.dark_store.latitude), float(slot.dark_store.longitude),
        )
    else:
        dist = 0.0

    from django.db.models import Count
    completions = DemandApplication.objects.filter(
        rider_id=app.rider_id, status="COMPLETED"
    ).count()

    score, _ = _compute_composite_score(
        distance_km  = dist,
        reliability  = float(rider.reliability_score or 0),
        completions  = completions,
        no_shows     = 0,
    )

    app.match_score = score
    app.save(update_fields=["match_score", "updated_at"])


@shared_task
def process_earnings_payout(application_id: str):
    """Queue earnings payout after check-out."""
    from marketplace_service.core.services import process_single_payout
    from marketplace_service.core.authentication import EarningsError
    try:
        process_single_payout(application_id)
    except EarningsError as e:
        logger.error("Payout failed for %s: %s — will retry", application_id, e)
        # Re-queue with delay
        process_earnings_payout.apply_async(
            args=[application_id], countdown=300, max_retries=5
        )


@shared_task
def expire_old_demand_slots():
    """Mark slots as EXPIRED if past their shift_date and not filled."""
    from marketplace_service.core.models import DemandSlot
    today = timezone.now().date()

    expired = DemandSlot.objects.filter(
        shift_date__lt = today,
        status__in     = ["PUBLISHED", "PARTIALLY_FILLED", "DRAFT"],
    )
    count = expired.update(status="EXPIRED")
    logger.info("Expired %d demand slots", count)
    return {"expired": count}


@shared_task
def auto_confirm_shortlisted_applications():
    """
    Auto-confirm SHORTLISTED applications for slots starting in <4 hours
    when slot still has open spots.
    """
    from marketplace_service.core.models import DemandApplication, DemandSlot
    from marketplace_service.core.services import decide_application
    from datetime import datetime, timedelta

    cutoff = timezone.now() + timedelta(hours=4)
    service_admin_id = "system"

    slots = DemandSlot.objects.filter(
        status__in=["PUBLISHED", "PARTIALLY_FILLED"],
    ).filter(
        shift_date__lte=cutoff.date(),
    )

    confirmed = 0
    for slot in slots:
        if slot.spots_remaining <= 0:
            continue

        shortlisted = DemandApplication.objects.filter(
            demand_slot = slot,
            status      = "SHORTLISTED",
        ).order_by("-match_score")[:slot.spots_remaining]

        for app in shortlisted:
            try:
                decide_application(str(app.id), "CONFIRM", service_admin_id)
                confirmed += 1
            except Exception as e:
                logger.warning("Auto-confirm failed for %s: %s", app.id, e)

    logger.info("Auto-confirmed %d shortlisted applications", confirmed)
    return {"confirmed": confirmed}


@shared_task
def compute_fill_rates():
    """Recompute fill_rate_pct for all active slots."""
    from marketplace_service.core.models import DemandSlot, DemandApplication
    from django.db.models import Count, Q
    from decimal import Decimal

    slots = DemandSlot.objects.filter(
        status__in=["PUBLISHED", "PARTIALLY_FILLED", "FILLED"]
    )
    for slot in slots:
        confirmed = DemandApplication.objects.filter(
            demand_slot=slot,
            status__in=["CONFIRMED", "COMPLETED"],
        ).count()
        slot.riders_confirmed = confirmed
        slot.fill_rate_pct    = Decimal(slot.fill_rate)
        if confirmed >= slot.riders_required and slot.status != "FILLED":
            slot.status = "FILLED"
        slot.save(update_fields=["riders_confirmed", "fill_rate_pct", "status", "updated_at"])

    logger.info("Recomputed fill rates for %d slots", slots.count())


# ── Notification stubs ────────────────────────────────────────

@shared_task
def notify_application_confirmed(application_id: str):
    from marketplace_service.core.models import DemandApplication
    try:
        app = DemandApplication.objects.select_related("demand_slot").get(id=application_id)
        logger.info(
            "[NOTIFY] Rider %s confirmed for '%s' on %s",
            app.rider_id, app.demand_slot.title, app.demand_slot.shift_date,
        )
    except DemandApplication.DoesNotExist:
        pass


@shared_task
def notify_application_rejected(application_id: str, reason: str):
    logger.info("[NOTIFY] Application %s rejected. Reason: %s", application_id, reason)


@shared_task
def notify_slot_cancelled(slot_id: str, reason: str):
    from marketplace_service.core.models import DemandApplication
    affected = DemandApplication.objects.filter(
        demand_slot_id=slot_id, status__in=["CONFIRMED", "SHORTLISTED"]
    ).values_list("rider_id", flat=True)
    logger.warning(
        "[NOTIFY] Slot %s cancelled. Reason: %s. Notifying %d riders.",
        slot_id, reason, len(affected),
    )
