"""
skills_service/core/views.py

APIs:
  GET/POST  /skills/modules/
  GET/PATCH /skills/modules/{id}/
  POST      /skills/modules/{id}/publish/
  GET/POST  /skills/modules/{id}/videos/
  GET       /skills/videos/{id}/
  POST      /skills/videos/{id}/watch/         ← rider logs watch progress
  POST      /skills/videos/{id}/quiz/          ← rider submits quiz answers
  GET       /skills/riders/{rider_id}/progress/
  GET       /skills/riders/{rider_id}/gamification/
  GET       /skills/riders/{rider_id}/badges/
  GET       /skills/riders/{rider_id}/onboarding-readiness/
  GET       /skills/leaderboard/
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import SkillModule, SkillVideo, RiderSkillProgress, RiderGamification, RiderBadge
from .serializers import (
    SkillModuleSerializer, SkillModuleCreateSerializer,
    SkillVideoSerializer, SkillVideoCreateSerializer,
    RiderProgressSerializer, VideoWatchSerializer, QuizSubmitSerializer,
    GamificationSerializer, BadgeSerializer, OnboardingProgressSerializer,
)
from .services import (
    record_video_watch, submit_quiz, get_onboarding_readiness, get_or_create_gamification,
)
from .authentication import (
    JWTAuthentication, IsAdminUser, IsRider, IsRiderOrAdmin, IsOpsOrAbove, StandardPagination,
)

logger = logging.getLogger(__name__)

def ok(data, code=200): return Response({"success": True, "data": data}, status=code)
def err(msg, code=400): return Response({"success": False, "error": {"message": msg, "code": code}}, status=code)


class ModuleListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request):
        from .authentication import AuthenticatedRider
        qs = SkillModule.objects.prefetch_related("videos")
        if isinstance(request.user, AuthenticatedRider):
            qs = qs.filter(is_published=True)
        else:
            published = request.query_params.get("published")
            if published == "true": qs = qs.filter(is_published=True)
        pager = StandardPagination()
        return pager.get_paginated_response(SkillModuleSerializer(pager.paginate_queryset(qs, request), many=True).data)

    def post(self, request):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        s = SkillModuleCreateSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        module = SkillModule.objects.create(**s.validated_data, created_by_id=str(request.user.id))
        return ok(SkillModuleSerializer(module).data, 201)


class ModuleDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def _get(self, module_id):
        try:
            return SkillModule.objects.prefetch_related("videos").get(id=module_id)
        except SkillModule.DoesNotExist:
            return None

    def get(self, request, module_id):
        m = self._get(module_id)
        if not m: return err("Module not found.", 404)
        return ok(SkillModuleSerializer(m).data)

    def patch(self, request, module_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        m = self._get(module_id)
        if not m: return err("Module not found.", 404)
        s = SkillModuleCreateSerializer(data=request.data, partial=True)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        for field, value in s.validated_data.items():
            setattr(m, field, value)
        m.save()
        return ok(SkillModuleSerializer(m).data)


class ModulePublishView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, module_id):
        try:
            module = SkillModule.objects.get(id=module_id)
        except SkillModule.DoesNotExist:
            return err("Module not found.", 404)
        module.is_published = not module.is_published
        module.save(update_fields=["is_published","updated_at"])
        status = "published" if module.is_published else "unpublished"
        return ok({"message": f"Module {status}.", "is_published": module.is_published})


class VideoListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, module_id):
        from .authentication import AuthenticatedRider
        qs = SkillVideo.objects.filter(module_id=module_id)
        if isinstance(request.user, AuthenticatedRider):
            qs = qs.filter(is_published=True)
        return ok(SkillVideoSerializer(qs, many=True).data)

    def post(self, request, module_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        try:
            module = SkillModule.objects.get(id=module_id)
        except SkillModule.DoesNotExist:
            return err("Module not found.", 404)
        s = SkillVideoCreateSerializer(data={**request.data, "module_id": str(module_id)})
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        video = SkillVideo.objects.create(**s.validated_data, module=module)
        return ok(SkillVideoSerializer(video).data, 201)


class VideoWatchView(APIView):
    """POST /skills/videos/{id}/watch/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, video_id):
        s = VideoWatchSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            progress = record_video_watch(
                rider_id        = str(request.user.id),
                video_id        = str(video_id),
                watch_time_secs = s.validated_data["watch_time_secs"],
                completed       = s.validated_data["completed"],
            )
            return ok(RiderProgressSerializer(progress).data)
        except ValueError as e:
            return err(str(e), 404)
        except Exception as e:
            logger.exception("Video watch recording failed")
            return err(str(e), 500)


class QuizSubmitView(APIView):
    """POST /skills/videos/{id}/quiz/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, video_id):
        s = QuizSubmitSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            result = submit_quiz(
                rider_id = str(request.user.id),
                video_id = str(video_id),
                answers  = s.validated_data["answers"],
            )
            return ok(result)
        except ValueError as e:
            return err(str(e), 422)
        except Exception as e:
            logger.exception("Quiz submission failed")
            return err(str(e), 500)


class RiderProgressView(APIView):
    """GET /skills/riders/{rider_id}/progress/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)
        qs = RiderSkillProgress.objects.filter(rider_id=rider_id).select_related("video","module")
        module_id = request.query_params.get("module_id")
        if module_id: qs = qs.filter(module_id=module_id)
        pager = StandardPagination()
        return pager.get_paginated_response(RiderProgressSerializer(pager.paginate_queryset(qs, request), many=True).data)


class GamificationView(APIView):
    """GET /skills/riders/{rider_id}/gamification/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)
        g = get_or_create_gamification(str(rider_id))
        return ok(GamificationSerializer(g).data)


class BadgesView(APIView):
    """GET /skills/riders/{rider_id}/badges/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)
        badges = RiderBadge.objects.filter(rider_id=rider_id).order_by("earned_at")
        return ok(BadgeSerializer(badges, many=True).data)


class OnboardingReadinessView(APIView):
    """GET /skills/riders/{rider_id}/onboarding-readiness/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)
        data = get_onboarding_readiness(str(rider_id))
        s    = OnboardingProgressSerializer(data)
        return ok(s.data)


class LeaderboardView(APIView):
    """GET /skills/leaderboard/ — top riders by points"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request):
        top = RiderGamification.objects.order_by("-total_points")[:20]
        data = [
            {
                "rank":          i + 1,
                "rider_id":      str(g.rider_id),
                "total_points":  g.total_points,
                "current_level": g.current_level,
                "streak_days":   g.streak_days,
            }
            for i, g in enumerate(top)
        ]
        return ok({"leaderboard": data, "count": len(data)})
