"""skills_service/core/tasks.py"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task
def award_onboarding_completion_badge(rider_id: str):
    from skills_service.core.models import RiderBadge
    RiderBadge.objects.get_or_create(rider_id=rider_id, badge_code="COMPLIANT",
        defaults={"badge_name":"Fully Compliant","badge_name_hi":"पूरी तरह अनुपालक"})
    logger.info("Onboarding badge awarded to rider %s", rider_id)

@shared_task
def update_leaderboard_cache():
    from skills_service.core.models import RiderGamification
    import json
    from django.core.cache import cache
    top = list(RiderGamification.objects.order_by("-total_points")[:50].values("rider_id","total_points","current_level","streak_days"))
    cache.set("yana:skills:leaderboard", json.dumps([{**t,"rider_id": str(t["rider_id"])} for t in top]), timeout=900)
    logger.info("Leaderboard cache refreshed")
