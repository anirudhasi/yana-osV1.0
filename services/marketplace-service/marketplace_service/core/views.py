"""
marketplace_service/core/views.py

APIs:
  Clients:
    GET/POST   /marketplace/clients/
    GET/PATCH  /marketplace/clients/{id}/
    GET/POST   /marketplace/clients/{id}/dark-stores/
    GET/POST   /marketplace/clients/{id}/contracts/

  Demand Slots:
    GET/POST   /marketplace/slots/
    GET/PATCH  /marketplace/slots/{id}/
    POST       /marketplace/slots/{id}/publish/
    POST       /marketplace/slots/{id}/cancel/
    GET        /marketplace/slots/{id}/applications/
    GET        /marketplace/slots/{id}/matches/         ← matching engine results
    POST       /marketplace/slots/{id}/bulk-confirm/    ← bulk confirm top matches

  Applications (rider-facing):
    POST       /marketplace/slots/{id}/apply/
    DELETE     /marketplace/applications/{id}/withdraw/
    POST       /marketplace/applications/{id}/check-in/
    POST       /marketplace/applications/{id}/check-out/
    GET        /marketplace/riders/{rider_id}/applications/

  Admin decisions:
    POST       /marketplace/applications/{id}/decide/

  Bulk payout:
    POST       /marketplace/slots/{id}/payout/

  Analytics:
    GET        /marketplace/analytics/fill-rates/
    GET        /marketplace/analytics/dashboard/
"""
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Client, ClientDarkStore, ClientContract, DemandSlot, DemandApplication
from .serializers import (
    ClientSerializer, ClientCreateSerializer,
    DarkStoreSerializer, DarkStoreCreateSerializer,
    ContractSerializer, ContractCreateSerializer,
    DemandSlotSerializer, DemandSlotCreateSerializer, DemandSlotUpdateSerializer,
    ApplicationSerializer, ApplicationDecideSerializer,
    CheckInSerializer, CheckOutSerializer,
    EarningsPayoutSerializer, RiderMatchSerializer, FillRateSerializer,
)
from .services import (
    create_demand_slot, publish_demand_slot, cancel_demand_slot,
    apply_for_slot, decide_application, withdraw_application,
    record_check_in, record_check_out,
    process_single_payout, get_fill_rate_report,
)
from .authentication import (
    JWTAuthentication,
    IsAdminUser,
    IsRider,
    IsRiderOrAdmin,
    IsSalesOrAbove,
    IsOpsOrAbove,
)
from .exceptions import (
    SlotFullError,
    SlotNotPublishedError,
    AlreadyAppliedError,
    AttendanceError,
    EarningsError,
)
from .pagination import StandardPagination

logger = logging.getLogger(__name__)


def ok(data, code=200):
    return Response({"success": True, "data": data}, status=code)

def err(message, code=400):
    return Response({"success": False, "error": {"message": message, "code": code}}, status=code)


# ─── Client ───────────────────────────────────────────────────

class ClientListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = Client.objects.filter(is_active=True).order_by("name")
        q  = request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ClientSerializer(page, many=True).data)

    def post(self, request):
        if not IsSalesOrAbove().has_permission(request, self):
            return err("Sales-level access required.", 403)
        s = ClientCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        client = Client.objects.create(**s.validated_data, created_by_id=str(request.user.id))
        return ok(ClientSerializer(client).data, 201)


class ClientDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def _get(self, client_id):
        try:
            return Client.objects.get(id=client_id, is_active=True)
        except Client.DoesNotExist:
            return None

    def get(self, request, client_id):
        c = self._get(client_id)
        return ok(ClientSerializer(c).data) if c else err("Client not found.", 404)

    def patch(self, request, client_id):
        if not IsSalesOrAbove().has_permission(request, self):
            return err("Sales-level access required.", 403)
        c = self._get(client_id)
        if not c:
            return err("Client not found.", 404)
        for field in ["name", "category", "primary_contact_name",
                      "primary_contact_email", "primary_contact_phone", "logo_url"]:
            if field in request.data:
                setattr(c, field, request.data[field])
        c.save()
        return ok(ClientSerializer(c).data)


class DarkStoreListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, client_id):
        stores = ClientDarkStore.objects.filter(client_id=client_id, is_active=True)
        return ok(DarkStoreSerializer(stores, many=True).data)

    def post(self, request, client_id):
        if not IsSalesOrAbove().has_permission(request, self):
            return err("Sales-level access required.", 403)
        s = DarkStoreCreateSerializer(data={**request.data, "client_id": str(client_id)})
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        store = ClientDarkStore.objects.create(**s.validated_data)
        return ok(DarkStoreSerializer(store).data, 201)


class ContractListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSalesOrAbove]

    def get(self, request, client_id):
        contracts = ClientContract.objects.filter(client_id=client_id).select_related("dark_store")
        return ok(ContractSerializer(contracts, many=True).data)

    def post(self, request, client_id):
        s = ContractCreateSerializer(data={**request.data, "client_id": str(client_id)})
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        contract = ClientContract.objects.create(
            **s.validated_data, created_by_id=str(request.user.id)
        )
        return ok(ContractSerializer(contract).data, 201)


# ─── Demand Slots ─────────────────────────────────────────────

class DemandSlotListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request):
        qs = DemandSlot.objects.select_related("client", "dark_store").order_by(
            "shift_date", "shift_start_time"
        )

        # Riders see only published slots in their city
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider):
            qs = qs.filter(status__in=["PUBLISHED", "PARTIALLY_FILLED"])
            # City filter from rider profile (best effort)
            city = request.query_params.get("city_id")
            if city:
                qs = qs.filter(city_id=city)
        else:
            # Admin sees all
            status_filter = request.query_params.get("status")
            city_filter   = request.query_params.get("city_id")
            client_filter = request.query_params.get("client_id")
            date_filter   = request.query_params.get("shift_date")
            if status_filter: qs = qs.filter(status=status_filter)
            if city_filter:   qs = qs.filter(city_id=city_filter)
            if client_filter: qs = qs.filter(client_id=client_filter)
            if date_filter:   qs = qs.filter(shift_date=date_filter)

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(DemandSlotSerializer(page, many=True).data)

    def post(self, request):
        if not IsSalesOrAbove().has_permission(request, self):
            return err("Sales-level access required.", 403)
        s = DemandSlotCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            slot = create_demand_slot(dict(s.validated_data), str(request.user.id))
            return ok(DemandSlotSerializer(slot).data, 201)
        except Exception as e:
            logger.exception("Slot creation failed")
            return err(str(e), 500)


class DemandSlotDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def _get(self, slot_id):
        try:
            return DemandSlot.objects.select_related("client", "dark_store").get(id=slot_id)
        except DemandSlot.DoesNotExist:
            return None

    def get(self, request, slot_id):
        slot = self._get(slot_id)
        if not slot:
            return err("Slot not found.", 404)
        return ok(DemandSlotSerializer(slot).data)

    def patch(self, request, slot_id):
        if not IsSalesOrAbove().has_permission(request, self):
            return err("Sales-level access required.", 403)
        slot = self._get(slot_id)
        if not slot:
            return err("Slot not found.", 404)
        if slot.status not in ("DRAFT", "PUBLISHED"):
            return err("Cannot edit a slot in this status.", 422)
        s = DemandSlotUpdateSerializer(data=request.data, partial=True)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        for field, value in s.validated_data.items():
            setattr(slot, field, value)
        slot.save()
        return ok(DemandSlotSerializer(slot).data)


class DemandSlotPublishView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSalesOrAbove]

    def post(self, request, slot_id):
        try:
            slot = DemandSlot.objects.get(id=slot_id)
        except DemandSlot.DoesNotExist:
            return err("Slot not found.", 404)
        try:
            slot = publish_demand_slot(slot, str(request.user.id))
            return ok(DemandSlotSerializer(slot).data)
        except SlotNotPublishedError as e:
            return err(e.message, 422)


class DemandSlotCancelView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, slot_id):
        try:
            slot = DemandSlot.objects.get(id=slot_id)
        except DemandSlot.DoesNotExist:
            return err("Slot not found.", 404)
        try:
            slot = cancel_demand_slot(slot, str(request.user.id),
                                       request.data.get("reason", ""))
            return ok({"message": "Slot cancelled.", "status": slot.status})
        except SlotNotPublishedError as e:
            return err(e.message, 422)


class DemandSlotApplicationsView(APIView):
    """GET /marketplace/slots/{id}/applications/ — all applications for a slot."""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, slot_id):
        qs = DemandApplication.objects.filter(demand_slot_id=slot_id).order_by(
            "-match_score", "-applied_at"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ApplicationSerializer(page, many=True).data)


class DemandSlotMatchesView(APIView):
    """
    GET /marketplace/slots/{id}/matches/
    Returns pre-computed matching engine results from Redis cache.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, slot_id):
        from django.core.cache import cache
        cached = cache.get(f"yana:matches:{slot_id}")
        if cached:
            matches = json.loads(cached)
            return ok({
                "slot_id":       str(slot_id),
                "match_count":   len(matches),
                "matches":       matches[:int(request.query_params.get("limit", 20))],
                "source":        "cache",
            })

        # Run matching synchronously if not cached
        try:
            slot = DemandSlot.objects.select_related("dark_store").get(id=slot_id)
        except DemandSlot.DoesNotExist:
            return err("Slot not found.", 404)

        from .tasks import run_matching_for_slot
        run_matching_for_slot.delay(str(slot_id))
        return ok({"message": "Matching queued. Check back in a few seconds.", "match_count": 0})


class BulkConfirmView(APIView):
    """
    POST /marketplace/slots/{id}/bulk-confirm/
    Admin bulk-confirms the top N matched riders for a slot.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, slot_id):
        try:
            slot = DemandSlot.objects.get(id=slot_id)
        except DemandSlot.DoesNotExist:
            return err("Slot not found.", 404)

        n = int(request.data.get("count", slot.spots_remaining))
        n = min(n, slot.spots_remaining)

        # Get top-scored shortlisted or applied applications
        apps = DemandApplication.objects.filter(
            demand_slot=slot,
            status__in=["APPLIED", "SHORTLISTED"],
        ).order_by("-match_score")[:n]

        confirmed_ids = []
        errors        = []
        for app in apps:
            try:
                decide_application(str(app.id), "CONFIRM", str(request.user.id))
                confirmed_ids.append(str(app.id))
            except Exception as e:
                errors.append({"application_id": str(app.id), "error": str(e)})

        slot.refresh_from_db()
        return ok({
            "confirmed_count":  len(confirmed_ids),
            "confirmed_ids":    confirmed_ids,
            "errors":           errors,
            "slot_fill_rate":   slot.fill_rate,
            "spots_remaining":  slot.spots_remaining,
        })


# ─── Applications (rider-facing) ──────────────────────────────

class ApplyForSlotView(APIView):
    """POST /marketplace/slots/{id}/apply/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, slot_id):
        try:
            app = apply_for_slot(str(slot_id), str(request.user.id))
            return ok(ApplicationSerializer(app).data, 201)
        except SlotFullError as e:
            return err(e.message, 409)
        except SlotNotPublishedError as e:
            return err(e.message, 422)
        except AlreadyAppliedError as e:
            return err(e.message, 409)
        except Exception as e:
            logger.exception("Apply for slot failed")
            return err(str(e), 500)


class WithdrawApplicationView(APIView):
    """DELETE /marketplace/applications/{id}/withdraw/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def delete(self, request, application_id):
        try:
            app = withdraw_application(str(application_id), str(request.user.id))
            return ok({"message": "Application withdrawn.", "status": app.status})
        except EarningsError as e:
            return err(e.message, 422)


class ApplicationDecideView(APIView):
    """POST /marketplace/applications/{id}/decide/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, application_id):
        s = ApplicationDecideSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            app = decide_application(
                application_id   = str(application_id),
                action           = s.validated_data["action"],
                admin_id         = str(request.user.id),
                rejection_reason = s.validated_data.get("rejection_reason", ""),
            )
            return ok(ApplicationSerializer(app).data)
        except (SlotFullError, EarningsError, SlotNotPublishedError) as e:
            return err(e.message, 422)


class CheckInView(APIView):
    """POST /marketplace/applications/{id}/check-in/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, application_id):
        s = CheckInSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            app = record_check_in(
                application_id = str(application_id),
                rider_id       = str(request.user.id),
                lat            = float(s.validated_data["latitude"]) if s.validated_data.get("latitude") else None,
                lng            = float(s.validated_data["longitude"]) if s.validated_data.get("longitude") else None,
            )
            return ok({
                "message":     "Checked in successfully.",
                "check_in_at": app.check_in_at,
                "status":      app.status,
            })
        except AttendanceError as e:
            return err(e.message, 422)


class CheckOutView(APIView):
    """POST /marketplace/applications/{id}/check-out/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, application_id):
        s = CheckOutSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            app = record_check_out(
                application_id   = str(application_id),
                rider_id         = str(request.user.id),
                lat              = float(s.validated_data["latitude"]) if s.validated_data.get("latitude") else None,
                lng              = float(s.validated_data["longitude"]) if s.validated_data.get("longitude") else None,
                orders_completed = s.validated_data.get("orders_completed", 0),
            )
            return ok({
                "message":          "Checked out. Earnings processing.",
                "check_out_at":     app.check_out_at,
                "hours_worked":     float(app.hours_worked or 0),
                "orders_completed": app.orders_completed,
                "estimated_earnings": app.computed_earnings,
                "status":           app.status,
            })
        except AttendanceError as e:
            return err(e.message, 422)


class RiderApplicationsView(APIView):
    """GET /marketplace/riders/{rider_id}/applications/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)

        qs = DemandApplication.objects.filter(rider_id=rider_id).select_related(
            "demand_slot__client", "demand_slot__dark_store"
        ).order_by("-applied_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ApplicationSerializer(page, many=True).data)


# ─── Bulk payout ──────────────────────────────────────────────

class SlotPayoutView(APIView):
    """POST /marketplace/slots/{id}/payout/ — Pay all completed riders."""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, slot_id):
        s = EarningsPayoutSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        app_ids  = s.validated_data["application_ids"]
        override = s.validated_data.get("override_amount")

        results = {"paid": [], "failed": [], "skipped": []}

        for app_id in app_ids:
            try:
                app = DemandApplication.objects.get(
                    id=app_id, demand_slot_id=slot_id, status="COMPLETED"
                )
                process_single_payout(str(app.id), override_amount=override,
                                      admin_id=str(request.user.id))
                results["paid"].append(str(app_id))
            except DemandApplication.DoesNotExist:
                results["skipped"].append(str(app_id))
            except EarningsError as e:
                results["failed"].append({"id": str(app_id), "error": e.message})

        return ok(results)


# ─── Analytics ────────────────────────────────────────────────

class FillRateAnalyticsView(APIView):
    """GET /marketplace/analytics/fill-rates/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        data = get_fill_rate_report(
            city_id   = request.query_params.get("city_id"),
            client_id = request.query_params.get("client_id"),
            days      = int(request.query_params.get("days", 7)),
        )
        return ok({"count": len(data), "slots": data})


class MarketplaceDashboardView(APIView):
    """GET /marketplace/analytics/dashboard/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        from django.db.models import Sum, Count, Q, Avg
        from datetime import timedelta

        today = timezone.now().date()
        week  = today - timedelta(days=7)

        slots = DemandSlot.objects.aggregate(
            total              = Count("id"),
            published_today    = Count("id", filter=Q(shift_date=today, status__in=["PUBLISHED", "PARTIALLY_FILLED", "FILLED"])),
            filled_this_week   = Count("id", filter=Q(shift_date__gte=week, status="FILLED")),
            avg_fill_rate      = Avg("fill_rate_pct"),
        )

        apps = DemandApplication.objects.aggregate(
            total_apps        = Count("id"),
            confirmed_today   = Count("id", filter=Q(demand_slot__shift_date=today, status="CONFIRMED")),
            completed_week    = Count("id", filter=Q(demand_slot__shift_date__gte=week, status="COMPLETED")),
            no_shows_week     = Count("id", filter=Q(demand_slot__shift_date__gte=week, status="NO_SHOW")),
            earnings_paid_week = Sum("earnings_credited", filter=Q(demand_slot__shift_date__gte=week, earnings_paid_at__isnull=False)),
        )

        return ok({
            "slots":        slots,
            "applications": apps,
            "top_clients":  list(
                Client.objects.filter(is_active=True).annotate(
                    total_slots=Count("demand_slots"),
                ).order_by("-total_slots").values("id", "name", "total_slots")[:5]
            ),
        })
