"""skills_service/core/serializers.py"""
from rest_framework import serializers
from .models import SkillModule, SkillVideo, RiderSkillProgress, RiderGamification, RiderBadge


class SkillVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SkillVideo
        fields = [
            "id","module_id","title","title_hi","video_url","thumbnail_url",
            "duration_secs","sequence_order","points_reward",
            "has_quiz","quiz_pass_score","is_published","created_at",
        ]


class SkillVideoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SkillVideo
        fields = [
            "module_id","title","title_hi","video_url","thumbnail_url",
            "duration_secs","sequence_order","points_reward",
            "has_quiz","quiz_questions","quiz_pass_score",
        ]
    def validate_points_reward(self, v):
        if v < 0: raise serializers.ValidationError("Points must be non-negative.")
        return v


class SkillModuleSerializer(serializers.ModelSerializer):
    videos       = SkillVideoSerializer(many=True, read_only=True)
    video_count  = serializers.SerializerMethodField()

    class Meta:
        model  = SkillModule
        fields = [
            "id","title","title_hi","description","description_hi",
            "thumbnail_url","sequence_order","is_mandatory","is_published",
            "video_count","videos","created_at",
        ]

    def get_video_count(self, obj):
        return obj.videos.filter(is_published=True).count()


class SkillModuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SkillModule
        fields = ["title","title_hi","description","description_hi",
                  "thumbnail_url","sequence_order","is_mandatory"]


class RiderProgressSerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source="video.title", read_only=True)
    module_title = serializers.CharField(source="module.title", read_only=True)

    class Meta:
        model  = RiderSkillProgress
        fields = [
            "id","rider_id","module_id","module_title","video_id","video_title",
            "watch_time_secs","is_completed","completed_at",
            "quiz_score","quiz_passed","points_earned","started_at",
        ]


class VideoWatchSerializer(serializers.Serializer):
    watch_time_secs = serializers.IntegerField(min_value=0)
    completed       = serializers.BooleanField(default=False)


class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class GamificationSerializer(serializers.ModelSerializer):
    level_name = serializers.SerializerMethodField()
    next_level_pts = serializers.SerializerMethodField()

    class Meta:
        model  = RiderGamification
        fields = [
            "id","rider_id","total_points","current_level","level_name",
            "next_level_pts","streak_days","longest_streak","last_activity_at",
        ]

    def get_level_name(self, obj):
        names = ["Novice","Beginner","Learner","Skilled","Expert","Master","Legend"]
        return names[min(obj.current_level - 1, len(names) - 1)]

    def get_next_level_pts(self, obj):
        from django.conf import settings
        thresholds = settings.LEVEL_THRESHOLDS
        if obj.current_level < len(thresholds):
            return thresholds[obj.current_level]
        return None


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RiderBadge
        fields = ["id","rider_id","badge_code","badge_name","badge_name_hi",
                  "badge_icon_url","earned_at"]


class OnboardingProgressSerializer(serializers.Serializer):
    """Tells the rider app what they need to complete before activation."""
    mandatory_modules      = SkillModuleSerializer(many=True)
    completed_mandatory    = serializers.IntegerField()
    total_mandatory        = serializers.IntegerField()
    all_mandatory_complete = serializers.BooleanField()
    total_points           = serializers.IntegerField()
    current_level          = serializers.IntegerField()
