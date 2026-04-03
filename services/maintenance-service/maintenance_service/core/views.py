"""maintenance_service/core/views.py"""
import logging
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import MaintenanceLog, MaintenanceAlert, Vehicle
from .serializers import (
    MaintenanceLogSerializer, MaintenanceLogCreateSerializer,
    MaintenanceLogUpdateSerializer, MaintenanceAlertSerializer,
)
from .authentication import JWTAuthentication, IsAdminUser, IsOpsOrAbove, StandardPagination

logger = logging.getLogger(__name__)

def ok(data, code=200): return Response({"success": True, "data": data}, status=code)
def err(msg, code=400): return Response({"success": False, "error": {"message": msg, "code": code}}, status=code)


class MaintenanceLogListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = MaintenanceLog.objects.order_by("-created_at")
        for p, f in [("vehicle_id","vehicle_id"),("status","status"),("hub_id","hub_id"),("maintenance_type","maintenance_type")]:
            v = request.query_params.get(p)
            if v: qs = qs.filter(**{f: v})
        pager = StandardPagination()
        return pager.get_paginated_response(MaintenanceLogSerializer(pager.paginate_queryset(qs, request), many=True).data)

    def post(self, request):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        s = MaintenanceLogCreateSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        log = MaintenanceLog.objects.create(**s.validated_data, logged_by_id=str(request.user.id))
        # Put vehicle in MAINTENANCE status
        Vehicle.objects.filter(id=s.validated_data["vehicle_id"]).update(status="MAINTENANCE")
        return ok(MaintenanceLogSerializer(log).data, 201)


class MaintenanceLogDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request, log_id):
        try:
            log = MaintenanceLog.objects.get(id=log_id)
        except MaintenanceLog.DoesNotExist:
            return err("Log not found.", 404)
        return ok(MaintenanceLogSerializer(log).data)

    def patch(self, request, log_id):
        if not IsOpsOrAbove().has_permission(request, self):
            return err("Ops-level access required.", 403)
        try:
            log = MaintenanceLog.objects.get(id=log_id)
        except MaintenanceLog.DoesNotExist:
            return err("Log not found.", 404)
        s = MaintenanceLogUpdateSerializer(data=request.data, partial=True)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)

        for field, value in s.validated_data.items():
            setattr(log, field, value)

        # Auto-set timestamps
        if s.validated_data.get("status") == "IN_PROGRESS" and not log.started_at:
            log.started_at = timezone.now()
        elif s.validated_data.get("status") == "COMPLETED":
            if not log.completed_at:
                log.completed_at = timezone.now()
            if log.started_at:
                delta = (log.completed_at - log.started_at).total_seconds() / 3600
                log.downtime_hours = round(delta, 2)
            # Restore vehicle to AVAILABLE
            Vehicle.objects.filter(id=log.vehicle_id).update(
                status="AVAILABLE",
                next_service_km=log.next_service_km,
                next_service_date=log.next_service_date,
            )
            # Dismiss related alerts
            MaintenanceAlert.objects.filter(
                vehicle_id=log.vehicle_id, is_acknowledged=False,
                alert_type__in=["SERVICE_DUE_DATE","SERVICE_DUE_ODOMETER"]
            ).update(is_acknowledged=True, acknowledged_at=timezone.now())

        log.save()
        return ok(MaintenanceLogSerializer(log).data)


class AlertListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        qs = MaintenanceAlert.objects.order_by("-created_at")
        if request.query_params.get("unresolved") == "true":
            qs = qs.filter(is_acknowledged=False)
        if request.query_params.get("severity"):
            qs = qs.filter(severity=request.query_params["severity"].upper())
        if request.query_params.get("vehicle_id"):
            qs = qs.filter(vehicle_id=request.query_params["vehicle_id"])
        pager = StandardPagination()
        return pager.get_paginated_response(MaintenanceAlertSerializer(pager.paginate_queryset(qs, request), many=True).data)


class AlertAcknowledgeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsOpsOrAbove]

    def post(self, request, alert_id):
        try:
            alert = MaintenanceAlert.objects.get(id=alert_id)
        except MaintenanceAlert.DoesNotExist:
            return err("Alert not found.", 404)
        alert.is_acknowledged    = True
        alert.acknowledged_by_id = str(request.user.id)
        alert.acknowledged_at    = timezone.now()
        alert.save(update_fields=["is_acknowledged","acknowledged_by_id","acknowledged_at"])
        return ok(MaintenanceAlertSerializer(alert).data)


class CostAnalyticsView(APIView):
    """GET /maintenance/analytics/costs/ — per-vehicle cost report"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def get(self, request):
        from datetime import timedelta
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)

        stats = (
            MaintenanceLog.objects.filter(
                status="COMPLETED", completed_at__gte=since
            )
            .values("vehicle_id")
            .annotate(
                total_logs   = Count("id"),
                total_cost   = Sum("labour_cost") + Sum("parts_cost"),
                total_labour = Sum("labour_cost"),
                total_parts  = Sum("parts_cost"),
                total_downtime = Sum("downtime_hours"),
            )
            .order_by("-total_cost")[:50]
        )

        # Join with vehicle registration numbers
        vehicle_ids  = [s["vehicle_id"] for s in stats]
        reg_map      = dict(Vehicle.objects.filter(id__in=vehicle_ids).values_list("id","registration_number"))

        result = []
        for s in stats:
            result.append({
                "vehicle_id":           str(s["vehicle_id"]),
                "registration_number":  reg_map.get(s["vehicle_id"], "UNKNOWN"),
                "total_logs":           s["total_logs"],
                "total_cost":           float(s["total_cost"] or 0),
                "total_labour":         float(s["total_labour"] or 0),
                "total_parts":          float(s["total_parts"] or 0),
                "total_downtime_hrs":   float(s["total_downtime"] or 0),
                "avg_cost_per_service": round(float(s["total_cost"] or 0) / max(s["total_logs"], 1), 2),
            })

        summary = MaintenanceLog.objects.filter(status="COMPLETED", completed_at__gte=since).aggregate(
            grand_total   = Sum("labour_cost") + Sum("parts_cost"),
            total_labour  = Sum("labour_cost"),
            total_parts   = Sum("parts_cost"),
            total_services = Count("id"),
            avg_downtime  = Avg("downtime_hours"),
        )

        return ok({
            "period_days":    days,
            "summary": {
                "grand_total":    float(summary["grand_total"] or 0),
                "total_labour":   float(summary["total_labour"] or 0),
                "total_parts":    float(summary["total_parts"] or 0),
                "total_services": summary["total_services"] or 0,
                "avg_downtime_hrs": float(summary["avg_downtime"] or 0),
            },
            "by_vehicle": result,
        })
