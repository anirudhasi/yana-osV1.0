"""
rider_service/core/views.py

Rider Onboarding API:
  POST   /riders/                       — Create rider
  GET    /riders/                       — List riders (admin only)
  GET    /riders/{id}/                  — Get rider profile
  PATCH  /riders/{id}/profile/          — Update profile
  POST   /riders/{id}/kyc/details/      — Submit KYC details (PII)
  POST   /riders/{id}/kyc/documents/    — Upload document
  GET    /riders/{id}/kyc/documents/    — List documents
  POST   /riders/{id}/kyc/decide/       — Admin: approve/reject KYC
  POST   /riders/{id}/documents/{doc_id}/decide/ — Admin: per-document decision
  GET    /riders/{id}/onboarding-status/ — Get onboarding progress
  POST   /riders/{id}/activate/         — Admin: activate rider
  POST   /riders/{id}/nominees/         — Add nominee
  GET    /riders/{id}/kyc/logs/         — KYC audit log
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Rider, RiderDocument, KYCVerificationLog
from .serializers import (
    CreateRiderSerializer,
    UpdateRiderProfileSerializer,
    SubmitKYCDetailsSerializer,
    NomineeSerializer,
    AdminKYCDecisionSerializer,
    DocumentKYCDecisionSerializer,
    RiderProfileSerializer,
    RiderListSerializer,
    OnboardingStatusSerializer,
    DocumentResponseSerializer,
    KYCLogSerializer,
)
from .services import (
    create_rider,
    update_rider_profile,
    upload_kyc_document,
    submit_kyc_details,
    upsert_nominee,
    admin_kyc_decision,
    admin_document_decision,
    activate_rider,
)
from .permissions import IsRider, IsAdminUser, IsOpsOrAbove, IsRiderOrAdmin
from .exceptions import ValidationError, KYCTransitionError, RiderStatusTransitionError, StorageError
from .authentication import JWTAuthentication

logger = logging.getLogger(__name__)


def ok(data, code=200):
    return Response({"success": True, "data": data}, status=code)


def err(message, code=400):
    return Response({"success": False, "error": {"message": message, "code": code}}, status=code)


def _get_rider_or_404(rider_id: str) -> Rider:
    try:
        return Rider.objects.get(id=rider_id, deleted_at__isnull=True)
    except (Rider.DoesNotExist, Exception):
        return None


# ─── Rider List + Create ──────────────────────────────────────

class RiderListCreateView(APIView):
    """
    GET  /riders/   — Admin: list all riders with filters
    POST /riders/   — Create new rider (admin or self)
    """
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [IsAdminUser()]

    def get(self, request):
        qs = Rider.objects.filter(deleted_at__isnull=True).order_by("-created_at")

        # Filters
        status_filter = request.query_params.get("status")
        kyc_filter    = request.query_params.get("kyc_status")
        hub_filter    = request.query_params.get("hub_id")
        city_filter   = request.query_params.get("city_id")
        search        = request.query_params.get("q")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if kyc_filter:
            qs = qs.filter(kyc_status=kyc_filter)
        if hub_filter:
            qs = qs.filter(hub_id=hub_filter)
        if city_filter:
            qs = qs.filter(city_id=city_filter)
        if search:
            qs = qs.filter(full_name__icontains=search) | qs.filter(phone__icontains=search)

        from .pagination import StandardPagination
        paginator   = StandardPagination()
        page        = paginator.paginate_queryset(qs, request)
        serializer  = RiderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateRiderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rider = create_rider(serializer.validated_data)
            return ok(RiderProfileSerializer(rider).data, 201)
        except ValidationError as e:
            return err(e.message, 409)
        except Exception as e:
            logger.exception("Unexpected error creating rider")
            return err(str(e), 500)


# ─── Rider Detail ─────────────────────────────────────────────

class RiderDetailView(APIView):
    """
    GET /riders/{id}/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)
        return ok(RiderProfileSerializer(rider).data)


# ─── Profile Update ───────────────────────────────────────────

class RiderProfileUpdateView(APIView):
    """
    PATCH /riders/{id}/profile/
    Rider can update own non-sensitive profile.
    Admin can update any rider.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def patch(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)

        serializer = UpdateRiderProfileSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rider = update_rider_profile(rider, serializer.validated_data)
            return ok(RiderProfileSerializer(rider).data)
        except Exception as e:
            logger.exception("Profile update failed")
            return err(str(e), 500)


# ─── KYC Details Submission ───────────────────────────────────

class KYCDetailsView(APIView):
    """
    POST /riders/{id}/kyc/details/
    Rider submits Aadhaar, PAN, DL, bank details.
    Fields are encrypted before storage.
    Triggers background Celery verification task.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def post(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)

        serializer = SubmitKYCDetailsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rider = submit_kyc_details(rider, serializer.validated_data)

            # Trigger async KYC verification
            from .tasks import run_kyc_verification
            run_kyc_verification.delay(str(rider.id))

            return ok({
                "message":    "KYC details submitted. Verification in progress.",
                "kyc_status": rider.kyc_status,
                "status":     rider.status,
            })
        except KYCTransitionError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("KYC detail submission failed")
            return err(str(e), 500)


# ─── Document Upload ──────────────────────────────────────────

class KYCDocumentUploadView(APIView):
    """
    POST /riders/{id}/kyc/documents/     — Upload a document file
    GET  /riders/{id}/kyc/documents/     — List uploaded documents
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]
    parser_classes         = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)
        docs = rider.documents.order_by("document_type", "-created_at")
        return ok(DocumentResponseSerializer(docs, many=True).data)

    def post(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)

        document_type = request.data.get("document_type", "").upper()
        file          = request.FILES.get("file")

        if not document_type:
            return err("'document_type' field is required.", 400)
        if not file:
            return err("'file' upload is required.", 400)

        valid_types = {c[0] for c in RiderDocument._meta.get_field("document_type").choices}
        if document_type not in valid_types:
            return err(f"Invalid document_type. Choose from: {', '.join(sorted(valid_types))}", 400)

        try:
            doc = upload_kyc_document(rider, file, document_type)
            return ok(DocumentResponseSerializer(doc).data, 201)
        except ValidationError as e:
            return err(e.message, 400)
        except StorageError as e:
            return err(f"File upload failed: {e}", 502)
        except Exception as e:
            logger.exception("Document upload failed")
            return err(str(e), 500)


# ─── Admin KYC Decision ───────────────────────────────────────

class AdminKYCDecisionView(APIView):
    """
    POST /riders/{id}/kyc/decide/
    Admin approves or rejects KYC for a rider.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        serializer = AdminKYCDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rider = admin_kyc_decision(
                rider=rider,
                action=serializer.validated_data["action"],
                admin_id=str(request.user.id),
                rejection_reason=serializer.validated_data.get("rejection_reason"),
                notes=serializer.validated_data.get("notes"),
            )
            return ok({
                "message":    f"KYC {serializer.validated_data['action']}D successfully.",
                "rider_id":   str(rider.id),
                "kyc_status": rider.kyc_status,
                "status":     rider.status,
            })
        except KYCTransitionError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("KYC decision failed")
            return err(str(e), 500)


# ─── Per-Document Decision ────────────────────────────────────

class AdminDocumentDecisionView(APIView):
    """
    POST /riders/{id}/documents/{doc_id}/decide/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, rider_id, doc_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        serializer = DocumentKYCDecisionSerializer(data={
            **request.data, "document_id": str(doc_id)
        })
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            doc = admin_document_decision(
                document_id=str(doc_id),
                action=serializer.validated_data["action"],
                admin_id=str(request.user.id),
                rejection_reason=serializer.validated_data.get("rejection_reason"),
            )
            return ok(DocumentResponseSerializer(doc).data)
        except ValidationError as e:
            return err(e.message, 404)
        except Exception as e:
            logger.exception("Document decision failed")
            return err(str(e), 500)


# ─── Onboarding Status ────────────────────────────────────────

class OnboardingStatusView(APIView):
    """
    GET /riders/{id}/onboarding-status/
    Returns step-by-step onboarding progress for the rider app.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)
        return ok(OnboardingStatusSerializer(rider).data)


# ─── Activate Rider ───────────────────────────────────────────

class ActivateRiderView(APIView):
    """
    POST /riders/{id}/activate/
    Admin manually activates a rider after training.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        try:
            rider = activate_rider(rider, str(request.user.id))
            return ok({
                "message": "Rider activated successfully.",
                "status":  rider.status,
            })
        except RiderStatusTransitionError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("Rider activation failed")
            return err(str(e), 500)


# ─── Nominee ─────────────────────────────────────────────────

class NomineeView(APIView):
    """
    POST /riders/{id}/nominees/   — Add / update nominee
    GET  /riders/{id}/nominees/   — List nominees
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)
        from .serializers import NomineeResponseSerializer
        nominees = rider.nominees.all()
        return ok(NomineeResponseSerializer(nominees, many=True).data)

    def post(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        self.check_object_permissions(request, rider)

        serializer = NomineeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            nominee = upsert_nominee(rider, serializer.validated_data)
            from .serializers import NomineeResponseSerializer
            return ok(NomineeResponseSerializer(nominee).data, 201)
        except Exception as e:
            logger.exception("Nominee upsert failed")
            return err(str(e), 500)


# ─── KYC Audit Logs ──────────────────────────────────────────

class KYCLogsView(APIView):
    """
    GET /riders/{id}/kyc/logs/
    Admin-only view of all KYC actions.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, rider_id):
        rider = _get_rider_or_404(rider_id)
        if not rider:
            return err("Rider not found", 404)

        logs = KYCVerificationLog.objects.filter(
            rider=rider
        ).order_by("-created_at")[:50]

        return ok(KYCLogSerializer(logs, many=True).data)
