"""
skills_service/core/services.py

Gamification engine:
  - Points awarded on video completion and quiz pass
  - Level-up calculation
  - Streak tracking
  - Badge awarding logic
"""
import logging
from datetime import date, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    SkillModule, SkillVideo, RiderSkillProgress,
    RiderGamification, RiderBadge,
)

logger = logging.getLogger(__name__)


# ── Gamification helpers ──────────────────────────────────────

def get_or_create_gamification(rider_id: str) -> RiderGamification:
    g, _ = RiderGamification.objects.get_or_create(rider_id=rider_id)
    return g


def _compute_level(total_points: int) -> int:
    thresholds = settings.LEVEL_THRESHOLDS
    level = 1
    for i, threshold in enumerate(thresholds):
        if total_points >= threshold:
            level = i + 1
    return level


@transaction.atomic
def award_points(rider_id: str, points: int, reason: str = "") -> RiderGamification:
    g = RiderGamification.objects.select_for_update().get(rider_id=rider_id)
    g.total_points  += points
    new_level        = _compute_level(g.total_points)
    levelled_up      = new_level > g.current_level
    g.current_level  = new_level
    g.last_activity_at = timezone.now()

    # Streak calculation
    today = timezone.now().date()
    if g.last_activity_at:
        last_date = g.last_activity_at.date() if hasattr(g.last_activity_at, 'date') else g.last_activity_at
        if last_date == today - timedelta(days=1):
            g.streak_days    += 1
            g.longest_streak  = max(g.longest_streak, g.streak_days)
        elif last_date < today - timedelta(days=1):
            g.streak_days = 1
    else:
        g.streak_days = 1

    g.save()

    if levelled_up:
        logger.info("Rider %s levelled up to %d!", rider_id, new_level)
        _check_and_award_badges(rider_id, g)

    logger.info("Awarded %d pts to rider %s (%s). Total: %d, Level: %d",
                points, rider_id, reason, g.total_points, g.current_level)
    return g


def _check_and_award_badges(rider_id: str, gamification: RiderGamification):
    """Auto-award badges based on milestones."""
    existing = set(RiderBadge.objects.filter(rider_id=rider_id).values_list("badge_code", flat=True))

    candidates = []

    if gamification.current_level >= 3 and "QUICK_LEARNER" not in existing:
        candidates.append(("QUICK_LEARNER", "Quick Learner", "तेज़ सीखने वाला"))

    if gamification.current_level >= 5 and "VETERAN" not in existing:
        candidates.append(("VETERAN", "Veteran Rider", "अनुभवी राइडर"))

    if gamification.streak_days >= 7 and "CONSISTENT" not in existing:
        candidates.append(("CONSISTENT", "Consistent Performer", "नियमित प्रदर्शनकर्ता"))

    # Check completions
    completed_modules = RiderSkillProgress.objects.filter(
        rider_id=rider_id, is_completed=True
    ).values("module_id").distinct().count()

    if completed_modules >= 5 and "COMPLIANT" not in existing:
        candidates.append(("COMPLIANT", "Fully Compliant", "पूरी तरह अनुपालक"))

    for code, name, name_hi in candidates:
        RiderBadge.objects.get_or_create(
            rider_id=rider_id,
            badge_code=code,
            defaults={
                "badge_name":    name,
                "badge_name_hi": name_hi,
            },
        )
        logger.info("Badge awarded: %s → rider %s", code, rider_id)


# ── Video Progress ────────────────────────────────────────────

@transaction.atomic
def record_video_watch(
    rider_id:        str,
    video_id:        str,
    watch_time_secs: int,
    completed:       bool,
) -> RiderSkillProgress:
    """
    Update rider's progress for a video.
    Awards points on first completion.
    """
    try:
        video = SkillVideo.objects.select_related("module").get(id=video_id, is_published=True)
    except SkillVideo.DoesNotExist:
        raise ValueError(f"Video {video_id} not found or not published.")

    get_or_create_gamification(rider_id)

    progress, created = RiderSkillProgress.objects.get_or_create(
        rider_id = rider_id,
        video    = video,
        defaults = {"module": video.module},
    )

    # Always update watch time
    progress.watch_time_secs = max(progress.watch_time_secs, watch_time_secs)

    already_completed = progress.is_completed
    points_awarded    = 0

    if completed and not already_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.points_earned = video.points_reward
        points_awarded = video.points_reward

        # Award points
        award_points(rider_id, points_awarded, f"Completed video: {video.title}")

    progress.save()

    # Check if entire module is now complete
    if completed:
        _check_module_completion(rider_id, video.module)

    return progress


@transaction.atomic
def submit_quiz(rider_id: str, video_id: str, answers: list) -> dict:
    """
    Grade a quiz submission.
    Awards bonus points on pass.
    """
    try:
        video = SkillVideo.objects.get(id=video_id, has_quiz=True, is_published=True)
    except SkillVideo.DoesNotExist:
        raise ValueError("Video not found or has no quiz.")

    questions = video.quiz_questions or []
    if not questions:
        raise ValueError("No quiz questions configured for this video.")

    if len(answers) != len(questions):
        raise ValueError(f"Expected {len(questions)} answers, got {len(answers)}.")

    # Grade
    correct  = sum(1 for q, a in zip(questions, answers) if q.get("answer") == a)
    score_pct = round(correct * 100 / len(questions))
    passed    = score_pct >= video.quiz_pass_score

    # Update progress record
    progress, _ = RiderSkillProgress.objects.get_or_create(
        rider_id=rider_id, video=video, defaults={"module": video.module}
    )
    progress.quiz_score  = score_pct
    progress.quiz_passed = passed
    progress.save(update_fields=["quiz_score","quiz_passed"])

    if passed:
        bonus = settings.POINTS_PER_QUIZ_PASS
        award_points(rider_id, bonus, f"Quiz passed: {video.title}")

    return {
        "score_pct":   score_pct,
        "passed":      passed,
        "correct":     correct,
        "total":       len(questions),
        "pass_score":  video.quiz_pass_score,
        "points_awarded": settings.POINTS_PER_QUIZ_PASS if passed else 0,
    }


def _check_module_completion(rider_id: str, module: SkillModule):
    """Award module-completion bonus if all published videos are done."""
    total_videos    = module.videos.filter(is_published=True).count()
    completed_count = RiderSkillProgress.objects.filter(
        rider_id=rider_id, module=module, is_completed=True
    ).count()

    if completed_count >= total_videos and total_videos > 0:
        bonus = settings.POINTS_PER_MODULE_COMPLETE
        award_points(rider_id, bonus, f"Module completed: {module.title}")
        logger.info("Rider %s completed module %s", rider_id, module.title)


# ── Onboarding readiness ──────────────────────────────────────

def get_onboarding_readiness(rider_id: str) -> dict:
    """Check if rider has completed all mandatory training modules."""
    mandatory = list(SkillModule.objects.filter(is_mandatory=True, is_published=True))
    g         = get_or_create_gamification(rider_id)

    completed_mandatory = 0
    for module in mandatory:
        total  = module.videos.filter(is_published=True).count()
        done   = RiderSkillProgress.objects.filter(
            rider_id=rider_id, module=module, is_completed=True
        ).count()
        if total > 0 and done >= total:
            completed_mandatory += 1

    return {
        "mandatory_modules":      mandatory,
        "completed_mandatory":    completed_mandatory,
        "total_mandatory":        len(mandatory),
        "all_mandatory_complete": completed_mandatory >= len(mandatory),
        "total_points":           g.total_points,
        "current_level":          g.current_level,
    }
