"""maintenance_service/core/serializers.py"""
from rest_framework import serializers
from .models import MaintenanceLog, MaintenanceAlert


class MaintenanceLogSerializer(serializers.ModelSerializer):
    total_cost = serializers.FloatField(read_only=True)
    class Meta:
        model  = MaintenanceLog
        fields = [
            "id","vehicle_id","hub_id","maintenance_type","status",
            "scheduled_date","started_at","completed_at","downtime_hours",
            "description","parts_replaced","labour_cost","parts_cost","total_cost",
            "odometer_at_service","next_service_km","next_service_date",
            "performed_by_vendor","invoice_url","logged_by_id","notes",
            "created_at","updated_at",
        ]


class MaintenanceLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MaintenanceLog
        fields = [
            "vehicle_id","hub_id","maintenance_type","scheduled_date",
            "description","parts_replaced","labour_cost","parts_cost",
            "odometer_at_service","next_service_km","next_service_date",
            "performed_by_vendor","invoice_url","notes",
        ]
    def validate_labour_cost(self, v):
        if v < 0: raise serializers.ValidationError("Labour cost cannot be negative.")
        return v


class MaintenanceLogUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MaintenanceLog
        fields = [
            "status","started_at","completed_at","downtime_hours",
            "labour_cost","parts_cost","parts_replaced","notes",
            "next_service_km","next_service_date","invoice_url",
        ]


class MaintenanceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MaintenanceAlert
        fields = [
            "id","vehicle_id","alert_type","severity","message",
            "is_acknowledged","acknowledged_by_id","acknowledged_at",
            "resolved_at","created_at",
        ]


class CostAnalyticsSerializer(serializers.Serializer):
    vehicle_id          = serializers.UUIDField()
    registration_number = serializers.CharField()
    total_logs          = serializers.IntegerField()
    total_cost          = serializers.FloatField()
    total_labour        = serializers.FloatField()
    total_parts         = serializers.FloatField()
    total_downtime_hrs  = serializers.FloatField()
    avg_cost_per_service = serializers.FloatField()
