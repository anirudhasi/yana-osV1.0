"""
fleet_service/core/views.py

Fleet APIs:
  Hubs:
    GET/POST   /fleet/hubs/
    GET/PATCH  /fleet/hubs/{id}/
    GET        /fleet/hubs/{id}/utilization/

  Vehicles:
    GET/POST   /fleet/vehicles/
    GET/PATCH/DELETE /fleet/vehicles/{id}/
    POST       /fleet/vehicles/{id}/status/
    GET        /fleet/vehicles/{id}/gps-history/
    GET        /fleet/vehicles/{id}/allotments/

  Allotments:
    GET/POST   /fleet/allotments/
    GET        /fleet/allotments/{id}/
    POST       /fleet/allotments/{id}/return/

  Alerts:
    GET        /fleet/alerts/
    POST       /fleet/alerts/{id}/acknowledge/

  Dashboard:
    GET        /fleet/dashboard/utilization/
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Vehicle, FleetHub, VehicleAllotment, MaintenanceAlert, City
from .serializers import (
    CitySerializer, FleetHubSerializer, FleetHubCreateSerializer,
    VehicleSerializer, VehicleCreateSerializer, VehicleUpdateSerializer,
    AllotmentSerializer, AllotmentCreateSerializer, AllotmentReturnSerializer,
    GPSHistorySerializer, MaintenanceAlertSerializer, HubUtilizationSerializer,
)
from .services import (
    create_hub, create_vehicle, update_vehicle,
    change_vehicle_status, soft_delete_vehicle,
    allocate_vehicle, return_vehicle,
    acknowledge_alert, get_hub_utilization,
)
from .authentication import JWTAuthentication, IsAdminUser, IsOpsOrAbove
from .exceptions import (
    AllotmentConflictError, VehicleStatusError, ReturnError, StandardPagination
)

logger = logging.getLogger(__name__)


def ok(data, code=200):
    return Response({"success": True, "data": data}, status=code)

def err(message, code=400):
    return Response({"success": False, "error": {"message": message, "code": code}}, status=code)


# ─── Cities ───────────────────────────────────────────────────

class CityListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        cities = City.objects.filter(is_active=True).order_by("name")
        return ok(CitySerializer(cities, many=True).data)


# ─── Hub views ────────────────────────────────────────────────

class HubListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = FleetHub.objects.filter(is_active=True).select_related("city").order_by("name")
        city_id = request.query_params.get("city_id")
        if city_id:
            qs = qs.filter(city_id=city_id)
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FleetHubSerializer(page, many=True).data)

    def post(self, request):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        s = FleetHubCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            hub = create_hub(s.validated_data, str(request.user.id))
            return ok(FleetHubSerializer(hub).data, 201)
        except VehicleStatusError as e:
            return err(e.message, 422)


class HubDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def _get_hub(self, hub_id):
        try:
            return FleetHub.objects.select_related("city").get(id=hub_id, is_active=True)
        except FleetHub.DoesNotExist:
            return None

    def get(self, request, hub_id):
        hub = self._get_hub(hub_id)
        if not hub:
            return err("Hub not found.", 404)
        return ok(FleetHubSerializer(hub).data)

    def patch(self, request, hub_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        hub = self._get_hub(hub_id)
        if not hub:
            return err("Hub not found.", 404)
        for field in ["name", "address", "capacity", "latitude", "longitude"]:
            if field in request.data:
                setattr(hub, field, request.data[field])
        hub.save()
        return ok(FleetHubSerializer(hub).data)


class HubUtilizationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, hub_id):
        data = get_hub_utilization(hub_ids=[hub_id])
        if not data:
            return err("Hub not found.", 404)
        return ok(data[0])


# ─── Vehicle views ────────────────────────────────────────────

class VehicleListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = Vehicle.objects.filter(
            deleted_at__isnull=True
        ).select_related("hub", "hub__city").order_by("-created_at")

        # Filters
        for param, field in [
            ("hub_id",  "hub_id"),
            ("status",  "status"),
            ("make",    "make__icontains"),
        ]:
            v = request.query_params.get(param)
            if v:
                qs = qs.filter(**{field: v})

        search = request.query_params.get("q")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(registration_number__icontains=search) |
                Q(make__icontains=search) |
                Q(model__icontains=search)
            )

        needs_service = request.query_params.get("needs_service")
        if needs_service == "true":
            from django.utils import timezone
            import datetime
            qs = qs.filter(
                next_service_date__lte=timezone.now().date() + datetime.timedelta(days=7)
            )

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(VehicleSerializer(page, many=True).data)

    def post(self, request):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        s = VehicleCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            vehicle = create_vehicle(dict(s.validated_data), str(request.user.id))
            return ok(VehicleSerializer(vehicle).data, 201)
        except VehicleStatusError as e:
            return err(e.message, 422)


class VehicleDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def _get(self, vehicle_id):
        try:
            return Vehicle.objects.select_related("hub", "hub__city").get(
                id=vehicle_id, deleted_at__isnull=True
            )
        except Vehicle.DoesNotExist:
            return None

    def get(self, request, vehicle_id):
        v = self._get(vehicle_id)
        if not v:
            return err("Vehicle not found.", 404)
        return ok(VehicleSerializer(v).data)

    def patch(self, request, vehicle_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        v = self._get(vehicle_id)
        if not v:
            return err("Vehicle not found.", 404)
        s = VehicleUpdateSerializer(data=request.data, partial=True)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            v = update_vehicle(v, dict(s.validated_data), str(request.user.id))
            return ok(VehicleSerializer(v).data)
        except VehicleStatusError as e:
            return err(e.message, 422)

    def delete(self, request, vehicle_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        v = self._get(vehicle_id)
        if not v:
            return err("Vehicle not found.", 404)
        try:
            soft_delete_vehicle(v, str(request.user.id))
            return ok({"message": "Vehicle retired successfully."})
        except VehicleStatusError as e:
            return err(e.message, 422)


class VehicleStatusChangeView(APIView):
    """POST /fleet/vehicles/{id}/status/ — Manual status override."""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, vehicle_id):
        new_status = request.data.get("status", "").upper()
        reason     = request.data.get("reason", "")
        if not new_status:
            return err("'status' field is required.", 400)
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, deleted_at__isnull=True)
        except Vehicle.DoesNotExist:
            return err("Vehicle not found.", 404)
        try:
            vehicle = change_vehicle_status(vehicle, new_status, str(request.user.id), reason)
            return ok({"status": vehicle.status, "message": f"Status changed to {new_status}."})
        except VehicleStatusError as e:
            return err(e.message, 422)


class VehicleGPSHistoryView(APIView):
    """GET /fleet/vehicles/{id}/gps-history/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, vehicle_id):
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, deleted_at__isnull=True)
        except Vehicle.DoesNotExist:
            return err("Vehicle not found.", 404)

        from .models import VehicleGPSTelemetry
        limit  = min(int(request.query_params.get("limit", 100)), 1000)
        points = VehicleGPSTelemetry.objects.filter(
            vehicle=vehicle
        ).order_by("-recorded_at")[:limit]
        return ok(GPSHistorySerializer(points, many=True).data)


class VehicleAllotmentsView(APIView):
    """GET /fleet/vehicles/{id}/allotments/ — allotment history for a vehicle."""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, vehicle_id):
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, deleted_at__isnull=True)
        except Vehicle.DoesNotExist:
            return err("Vehicle not found.", 404)

        qs = VehicleAllotment.objects.filter(vehicle=vehicle).order_by("-allotted_at")
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AllotmentSerializer(page, many=True).data)


# ─── Allotment views ──────────────────────────────────────────

class AllotmentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = VehicleAllotment.objects.select_related(
            "vehicle", "hub"
        ).order_by("-allotted_at")

        for param, field in [
            ("rider_id",   "rider_id"),
            ("vehicle_id", "vehicle_id"),
            ("hub_id",     "hub_id"),
            ("status",     "status"),
        ]:
            v = request.query_params.get(param)
            if v:
                qs = qs.filter(**{field: v})

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AllotmentSerializer(page, many=True).data)

    def post(self, request):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        s = AllotmentCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            allotment = allocate_vehicle(dict(s.validated_data), str(request.user.id))
            return ok(AllotmentSerializer(allotment).data, 201)
        except AllotmentConflictError as e:
            return err(e.message, 409)
        except VehicleStatusError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("Allotment failed")
            return err(str(e), 500)


class AllotmentDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, allotment_id):
        try:
            a = VehicleAllotment.objects.select_related("vehicle", "hub").get(id=allotment_id)
        except VehicleAllotment.DoesNotExist:
            return err("Allotment not found.", 404)
        return ok(AllotmentSerializer(a).data)


class AllotmentReturnView(APIView):
    """POST /fleet/allotments/{id}/return/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, allotment_id):
        s = AllotmentReturnSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)
        try:
            allotment = return_vehicle(allotment_id, dict(s.validated_data), str(request.user.id))
            return ok(AllotmentSerializer(allotment).data)
        except ReturnError as e:
            return err(e.message, 404)
        except Exception as e:
            logger.exception("Return failed")
            return err(str(e), 500)


# ─── Alert views ──────────────────────────────────────────────

class AlertListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = MaintenanceAlert.objects.select_related("vehicle").order_by("-created_at")

        if request.query_params.get("unresolved") == "true":
            qs = qs.filter(is_acknowledged=False)
        severity = request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity.upper())
        vehicle_id = request.query_params.get("vehicle_id")
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(MaintenanceAlertSerializer(page, many=True).data)


class AlertAcknowledgeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, alert_id):
        try:
            alert = acknowledge_alert(alert_id, str(request.user.id))
            return ok(MaintenanceAlertSerializer(alert).data)
        except VehicleStatusError as e:
            return err(e.message, 404)


# ─── Dashboard ────────────────────────────────────────────────

class FleetDashboardView(APIView):
    """GET /fleet/dashboard/utilization/ — Fleet-wide utilization summary."""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        import json
        from django.core.cache import cache

        city_id = request.query_params.get("city_id")

        # Try cache first
        cache_key = f"yana:fleet:hub_utilization"
        cached    = cache.get(cache_key)
        if cached and not city_id:
            return ok(json.loads(cached))

        hub_ids = None
        if city_id:
            hub_ids = list(FleetHub.objects.filter(
                city_id=city_id, is_active=True
            ).values_list("id", flat=True))

        data = get_hub_utilization(hub_ids=hub_ids)

        # Summary totals
        summary = {
            "total_hubs":      len(data),
            "total_vehicles":  sum(d["total_vehicles"] for d in data),
            "total_available": sum(d["available"] for d in data),
            "total_allocated": sum(d["allocated"] for d in data),
            "avg_utilization": round(
                sum(d["utilization_pct"] for d in data) / len(data), 2
            ) if data else 0.0,
        }

        return ok({"summary": summary, "hubs": data})
