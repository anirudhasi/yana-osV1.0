from django.urls import path
from .views import (
    RiderListCreateView,
    RiderDetailView,
    RiderProfileUpdateView,
    KYCDetailsView,
    KYCDocumentUploadView,
    AdminKYCDecisionView,
    AdminDocumentDecisionView,
    OnboardingStatusView,
    ActivateRiderView,
    NomineeView,
    KYCLogsView,
)

urlpatterns = [
    # Core CRUD
    path("",                                    RiderListCreateView.as_view(),      name="rider-list-create"),
    path("<uuid:rider_id>/",                    RiderDetailView.as_view(),          name="rider-detail"),
    path("<uuid:rider_id>/profile/",            RiderProfileUpdateView.as_view(),   name="rider-profile-update"),

    # KYC flow
    path("<uuid:rider_id>/kyc/details/",        KYCDetailsView.as_view(),           name="kyc-details"),
    path("<uuid:rider_id>/kyc/documents/",      KYCDocumentUploadView.as_view(),    name="kyc-documents"),
    path("<uuid:rider_id>/kyc/decide/",         AdminKYCDecisionView.as_view(),     name="kyc-decide"),
    path("<uuid:rider_id>/kyc/logs/",           KYCLogsView.as_view(),              name="kyc-logs"),

    # Per-document decision
    path("<uuid:rider_id>/documents/<uuid:doc_id>/decide/",
         AdminDocumentDecisionView.as_view(), name="document-decide"),

    # Onboarding status (rider app)
    path("<uuid:rider_id>/onboarding-status/",  OnboardingStatusView.as_view(),     name="onboarding-status"),

    # Admin actions
    path("<uuid:rider_id>/activate/",           ActivateRiderView.as_view(),        name="rider-activate"),

    # Nominees
    path("<uuid:rider_id>/nominees/",           NomineeView.as_view(),              name="rider-nominees"),
]
