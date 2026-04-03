from django.urls import path
from .views import (
    ModuleListCreateView, ModuleDetailView, ModulePublishView,
    VideoListCreateView, VideoWatchView, QuizSubmitView,
    RiderProgressView, GamificationView, BadgesView,
    OnboardingReadinessView, LeaderboardView,
)

urlpatterns = [
    path("modules/",                                      ModuleListCreateView.as_view(),    name="module-list"),
    path("modules/<uuid:module_id>/",                     ModuleDetailView.as_view(),        name="module-detail"),
    path("modules/<uuid:module_id>/publish/",             ModulePublishView.as_view(),       name="module-publish"),
    path("modules/<uuid:module_id>/videos/",              VideoListCreateView.as_view(),     name="video-list"),
    path("videos/<uuid:video_id>/watch/",                 VideoWatchView.as_view(),          name="video-watch"),
    path("videos/<uuid:video_id>/quiz/",                  QuizSubmitView.as_view(),          name="quiz-submit"),
    path("riders/<uuid:rider_id>/progress/",              RiderProgressView.as_view(),       name="rider-progress"),
    path("riders/<uuid:rider_id>/gamification/",          GamificationView.as_view(),        name="gamification"),
    path("riders/<uuid:rider_id>/badges/",                BadgesView.as_view(),              name="badges"),
    path("riders/<uuid:rider_id>/onboarding-readiness/",  OnboardingReadinessView.as_view(), name="onboarding-readiness"),
    path("leaderboard/",                                  LeaderboardView.as_view(),         name="leaderboard"),
]
