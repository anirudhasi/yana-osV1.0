"""skills_service/core/models.py"""
import uuid
from django.db import models

BADGE_CODES = [
    ("SAFETY_FIRST",   "Safety First"),
    ("SPEED_DEMON",    "Speed Demon"),
    ("CONSISTENT",     "Consistent Performer"),
    ("VETERAN",        "Veteran Rider"),
    ("TOP_EARNER",     "Top Earner"),
    ("QUICK_LEARNER",  "Quick Learner"),
    ("COMPLIANT",      "Fully Compliant"),
]

class SkillModule(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title          = models.CharField(max_length=300)
    title_hi       = models.CharField(max_length=300, null=True, blank=True)
    description    = models.TextField(null=True, blank=True)
    description_hi = models.TextField(null=True, blank=True)
    thumbnail_url  = models.TextField(null=True, blank=True)
    sequence_order = models.IntegerField(default=0)
    is_mandatory   = models.BooleanField(default=False)
    is_published   = models.BooleanField(default=False)
    created_by_id  = models.UUIDField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skill_modules"
        ordering = ["sequence_order"]

    def __str__(self):
        return f"{self.title} ({'mandatory' if self.is_mandatory else 'optional'})"


class SkillVideo(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module         = models.ForeignKey(SkillModule, on_delete=models.CASCADE, related_name="videos")
    title          = models.CharField(max_length=300)
    title_hi       = models.CharField(max_length=300, null=True, blank=True)
    video_url      = models.TextField()            # S3/MinIO path
    thumbnail_url  = models.TextField(null=True, blank=True)
    duration_secs  = models.IntegerField(null=True, blank=True)
    sequence_order = models.IntegerField(default=0)
    points_reward  = models.IntegerField(default=10)
    has_quiz       = models.BooleanField(default=False)
    quiz_questions = models.JSONField(null=True, blank=True)   # [{q, options, answer}]
    quiz_pass_score = models.IntegerField(default=70)          # % to pass
    is_published   = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skill_videos"
        ordering = ["module","sequence_order"]
        indexes  = [models.Index(fields=["module_id","sequence_order"])]

    def __str__(self):
        return f"{self.title} ({self.duration_secs}s, {self.points_reward}pts)"


class RiderSkillProgress(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id     = models.UUIDField(db_index=True)
    module       = models.ForeignKey(SkillModule, on_delete=models.CASCADE, related_name="progress")
    video        = models.ForeignKey(SkillVideo,  on_delete=models.CASCADE, related_name="progress")
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    watch_time_secs = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    quiz_score   = models.IntegerField(null=True, blank=True)
    quiz_passed  = models.BooleanField(null=True, blank=True)
    points_earned = models.IntegerField(default=0)

    class Meta:
        db_table     = "rider_skill_progress"
        unique_together = [["rider_id","video"]]
        indexes = [
            models.Index(fields=["rider_id"]),
            models.Index(fields=["rider_id","module_id"]),
        ]

    def __str__(self):
        return f"Progress(rider={self.rider_id}, video={self.video_id}, done={self.is_completed})"


class RiderGamification(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id       = models.UUIDField(unique=True)
    total_points   = models.IntegerField(default=0)
    current_level  = models.IntegerField(default=1)
    streak_days    = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rider_gamification"

    def __str__(self):
        return f"Gamification(rider={self.rider_id}, pts={self.total_points}, lvl={self.current_level})"


class RiderBadge(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_id     = models.UUIDField(db_index=True)
    badge_code   = models.CharField(max_length=50, choices=BADGE_CODES)
    badge_name   = models.CharField(max_length=100)
    badge_name_hi = models.CharField(max_length=100, null=True, blank=True)
    badge_icon_url = models.TextField(null=True, blank=True)
    earned_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = "rider_badges"
        unique_together = [["rider_id","badge_code"]]
        indexes = [models.Index(fields=["rider_id"])]

    def __str__(self):
        return f"Badge({self.badge_code}) → rider {self.rider_id}"
