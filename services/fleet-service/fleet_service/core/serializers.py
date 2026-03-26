"""fleet_service/core/serializers.py"""
import re
from rest_framework import serializers
from .models import City, FleetHub, Vehicle, VehicleAllotment, MaintenanceAlert, VehicleGPSTelemetry


# ── City ──────────────────────────────────────────────────────

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model  = City
        fields = ["id", "name", "state", "is_active", "created_at"]


# ── Hub ───────────────────────────────────────────────────────

class FleetHubSerializer(serializers.ModelSerializer):
    city_name       = serializers.CharField(source="city.name", read_only=True)
    available_count = serializers.SerializerMethodField()
    allocated_count = serializers.SerializerMethodField()
    utilization_pct = serializers.SerializerMethodField()

    class Meta:
        model  = FleetHub
        fields = [
            "id", "city_id", "city_name", "name", "address",
            "latitude", "longitude", "capacity", "is_active",
            "available_count", "allocated_count", "utilization_pct",
            "created_at",
        ]

    def get_available_count(self, obj): return obj.available_count
    def get_allocated_count(self, obj): return obj.allocated_count
    def get_utilization_pct(self, obj): return obj.utilization_pct


class FleetHubCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FleetHub
        fields = ["city_id", "name", "address", "latitude", "longitude", "capacity"]

    def validate_capacity(self, v):
        if v < 0:
            raise serializers.ValidationError("Capacity cannot be negative.")
        return v


# ── Vehicle ───────────────────────────────────────────────────

def _validate_reg_number(value: str) -> str:
    clean = value.upper().replace(" ", "").replace("-", "")
    # Indian registration: 2 letters + 2 digits + 1-2 letters + 4 digits
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$", clean):
        raise serializers.ValidationError(
            "Invalid registration number. Expected format: DL01AB1234"
        )
    return clean


class VehicleSerializer(serializers.ModelSerializer):
    hub_name          = serializers.CharField(source="hub.name", read_only=True)
    city_name         = serializers.CharField(source="hub.city.name", read_only=True)
    needs_service     = serializers.BooleanField(read_only=True)
    compliance_warnings = serializers.ListField(read_only=True)
    active_allotment_id = serializers.SerializerMethodField()

    class Meta:
        model  = Vehicle
        fields = [
            "id", "hub_id", "hub_name", "city_name",
            "registration_number", "chassis_number", "motor_number",
            "make", "model", "manufacturing_year", "color",
            "battery_capacity_kwh", "battery_health_pct",
            "range_km", "max_speed_kmh",
            "current_odometer_km",
            "last_gps_lat", "last_gps_lng", "last_gps_at",
            "battery_level_pct", "is_charging",
            "status",
            "purchase_price", "purchase_date",
            "insurance_expiry", "puc_expiry", "fitness_expiry",
            "next_service_km", "next_service_date",
            "needs_service", "compliance_warnings",
            "active_allotment_id",
            "created_at", "updated_at",
        ]

    def get_active_allotment_id(self, obj):
        allotment = obj.allotments.filter(status="ACTIVE").first()
        return str(allotment.id) if allotment else None


class VehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicle
        fields = [
            "hub_id", "registration_number", "chassis_number", "motor_number",
            "make", "model", "manufacturing_year", "color",
            "battery_capacity_kwh", "range_km", "max_speed_kmh",
            "purchase_price", "purchase_date",
            "insurance_expiry", "puc_expiry", "fitness_expiry",
        ]

    def validate_registration_number(self, v):
        return _validate_reg_number(v)

    def validate_manufacturing_year(self, v):
        import datetime
        if v and (v < 2015 or v > datetime.date.today().year + 1):
            raise serializers.ValidationError("Manufacturing year out of valid range.")
        return v

    def validate_battery_capacity_kwh(self, v):
        if v and (v <= 0 or v > 100):
            raise serializers.ValidationError("Battery capacity must be between 0 and 100 kWh.")
        return v


class VehicleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicle
        fields = [
            "hub_id", "make", "model", "color",
            "battery_health_pct", "battery_level_pct", "is_charging",
            "insurance_expiry", "puc_expiry", "fitness_expiry",
            "next_service_km", "next_service_date",
            "rc_document_url", "insurance_document_url",
        ]


# ── Allotment ─────────────────────────────────────────────────

class AllotmentSerializer(serializers.ModelSerializer):
    vehicle_reg = serializers.CharField(source="vehicle.registration_number", read_only=True)
    hub_name    = serializers.CharField(source="hub.name",                    read_only=True)
    km_driven   = serializers.FloatField(read_only=True)

    class Meta:
        model  = VehicleAllotment
        fields = [
            "id", "rider_id", "vehicle_id", "vehicle_reg",
            "hub_id", "hub_name",
            "allotted_at", "allotted_by_id",
            "expected_return_at", "returned_at",
            "odometer_at_allotment", "odometer_at_return",
            "battery_pct_at_allotment", "battery_pct_at_return",
            "condition_at_allotment", "condition_at_return",
            "damage_notes",
            "daily_rent_amount", "security_deposit",
            "deposit_refunded", "deposit_refund_amount",
            "status", "km_driven",
            "created_at", "updated_at",
        ]


class AllotmentCreateSerializer(serializers.Serializer):
    rider_id          = serializers.UUIDField()
    vehicle_id        = serializers.UUIDField()
    daily_rent_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    security_deposit  = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    expected_return_at = serializers.DateTimeField(required=False, allow_null=True)
    condition_at_allotment = serializers.CharField(required=False, allow_blank=True)

    def validate_daily_rent_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Daily rent must be positive.")
        return v


class AllotmentReturnSerializer(serializers.Serializer):
    returned_to_hub_id   = serializers.UUIDField(required=False, allow_null=True)
    odometer_at_return   = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    battery_pct_at_return = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    condition_at_return  = serializers.CharField(required=False, allow_blank=True)
    damage_notes         = serializers.CharField(required=False, allow_blank=True)
    refund_deposit       = serializers.BooleanField(default=True)
    deposit_refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    return_type          = serializers.ChoiceField(
        choices=["RETURNED", "FORCE_RETURNED", "EXPIRED"],
        default="RETURNED",
    )


# ── GPS ───────────────────────────────────────────────────────

class GPSHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = VehicleGPSTelemetry
        fields = ["id", "latitude", "longitude", "speed_kmh", "battery_pct", "odometer_km", "recorded_at"]


# ── Alerts ────────────────────────────────────────────────────

class MaintenanceAlertSerializer(serializers.ModelSerializer):
    vehicle_reg = serializers.CharField(source="vehicle.registration_number", read_only=True)

    class Meta:
        model  = MaintenanceAlert
        fields = [
            "id", "vehicle_id", "vehicle_reg",
            "alert_type", "severity", "message",
            "is_acknowledged", "acknowledged_at", "resolved_at",
            "created_at",
        ]


# ── Hub utilization summary ───────────────────────────────────

class HubUtilizationSerializer(serializers.Serializer):
    hub_id          = serializers.UUIDField()
    hub_name        = serializers.CharField()
    city_name       = serializers.CharField()
    capacity        = serializers.IntegerField()
    total_vehicles  = serializers.IntegerField()
    available       = serializers.IntegerField()
    allocated       = serializers.IntegerField()
    maintenance     = serializers.IntegerField()
    utilization_pct = serializers.FloatField()
