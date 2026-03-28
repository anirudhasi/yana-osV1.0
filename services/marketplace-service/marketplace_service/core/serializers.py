"""marketplace_service/core/serializers.py"""
import re
from decimal import Decimal
from rest_framework import serializers
from .models import Client, ClientDarkStore, ClientContract, DemandSlot, DemandApplication


# ── Client ────────────────────────────────────────────────────

class ClientSerializer(serializers.ModelSerializer):
    dark_store_count = serializers.SerializerMethodField()
    class Meta:
        model  = Client
        fields = [
            "id", "name", "category", "gstin", "pan",
            "primary_contact_name", "primary_contact_email", "primary_contact_phone",
            "logo_url", "is_active", "dark_store_count", "created_at",
        ]
    def get_dark_store_count(self, obj):
        return obj.dark_stores.filter(is_active=True).count()


class ClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Client
        fields = [
            "name", "category", "gstin", "pan",
            "primary_contact_name", "primary_contact_email", "primary_contact_phone",
            "logo_url",
        ]
    def validate_name(self, v):
        if Client.objects.filter(name__iexact=v.strip()).exists():
            raise serializers.ValidationError("A client with this name already exists.")
        return v.strip()


class DarkStoreSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    class Meta:
        model  = ClientDarkStore
        fields = [
            "id", "client_id", "client_name", "city_id", "hub_id",
            "name", "address", "latitude", "longitude", "is_active", "created_at",
        ]


class DarkStoreCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ClientDarkStore
        fields = ["client_id", "city_id", "hub_id", "name", "address", "latitude", "longitude"]


class ContractSerializer(serializers.ModelSerializer):
    client_name     = serializers.CharField(source="client.name",      read_only=True)
    dark_store_name = serializers.CharField(source="dark_store.name",  read_only=True)
    class Meta:
        model  = ClientContract
        fields = [
            "id", "client_id", "client_name",
            "dark_store_id", "dark_store_name",
            "contract_start", "contract_end",
            "pay_per_order", "pay_per_hour", "pay_per_shift",
            "minimum_guarantee", "pay_structure",
            "is_active", "document_url", "created_at",
        ]

    # Add pay_structure from demand slot
    pay_structure = serializers.SerializerMethodField()
    def get_pay_structure(self, obj):
        if obj.pay_per_order: return "PER_ORDER"
        if obj.pay_per_shift: return "PER_SHIFT"
        if obj.pay_per_hour:  return "PER_HOUR"
        return "UNKNOWN"


class ContractCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ClientContract
        fields = [
            "client_id", "dark_store_id",
            "contract_start", "contract_end",
            "pay_per_order", "pay_per_hour", "pay_per_shift",
            "minimum_guarantee", "sla_terms", "document_url",
        ]
    def validate(self, data):
        pay_fields = [data.get("pay_per_order"), data.get("pay_per_hour"), data.get("pay_per_shift")]
        if not any(pay_fields):
            raise serializers.ValidationError("At least one pay rate must be specified.")
        return data


# ── Demand Slot ───────────────────────────────────────────────

class DemandSlotSerializer(serializers.ModelSerializer):
    client_name     = serializers.CharField(source="client.name",      read_only=True)
    dark_store_name = serializers.CharField(source="dark_store.name",  read_only=True)
    dark_store_address = serializers.CharField(source="dark_store.address", read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True)
    fill_rate       = serializers.FloatField(read_only=True)
    is_full         = serializers.BooleanField(read_only=True)

    class Meta:
        model  = DemandSlot
        fields = [
            "id", "client_id", "client_name",
            "dark_store_id", "dark_store_name", "dark_store_address",
            "city_id", "title", "description",
            "shift_type", "shift_date",
            "shift_start_time", "shift_end_time", "shift_duration_hrs",
            "riders_required", "riders_confirmed", "riders_shown_up",
            "spots_remaining", "fill_rate", "is_full",
            "pay_structure",
            "pay_per_order", "pay_per_shift", "pay_per_hour",
            "earnings_estimate", "vehicle_required",
            "min_reliability_score", "badge_required",
            "status", "published_at", "expires_at",
            "fill_rate_pct",
            "created_at", "updated_at",
        ]


class DemandSlotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DemandSlot
        fields = [
            "client_id", "dark_store_id", "city_id",
            "title", "description", "shift_type",
            "shift_date", "shift_start_time", "shift_end_time", "shift_duration_hrs",
            "riders_required",
            "pay_structure", "pay_per_order", "pay_per_shift", "pay_per_hour",
            "earnings_estimate", "vehicle_required",
            "min_reliability_score", "required_hub_ids", "badge_required",
            "expires_at",
        ]

    def validate_riders_required(self, v):
        if v < 1 or v > 500:
            raise serializers.ValidationError("Riders required must be between 1 and 500.")
        return v

    def validate(self, data):
        from datetime import date
        if data.get("shift_date") and data["shift_date"] < date.today():
            raise serializers.ValidationError({"shift_date": "Shift date cannot be in the past."})
        if data.get("shift_start_time") and data.get("shift_end_time"):
            if data["shift_start_time"] >= data["shift_end_time"]:
                # Night shifts cross midnight — only validate same-day
                pass
        pay_fields = [data.get("pay_per_order"), data.get("pay_per_shift"), data.get("pay_per_hour")]
        if not any(pay_fields):
            raise serializers.ValidationError("At least one pay rate must be specified.")
        return data


class DemandSlotUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DemandSlot
        fields = [
            "title", "description", "riders_required",
            "pay_per_order", "pay_per_shift", "pay_per_hour", "earnings_estimate",
            "min_reliability_score", "required_hub_ids", "badge_required", "expires_at",
        ]


# ── Applications ──────────────────────────────────────────────

class ApplicationSerializer(serializers.ModelSerializer):
    slot_title       = serializers.CharField(source="demand_slot.title",          read_only=True)
    slot_date        = serializers.DateField(source="demand_slot.shift_date",      read_only=True)
    client_name      = serializers.CharField(source="demand_slot.client.name",    read_only=True)
    dark_store_name  = serializers.CharField(source="demand_slot.dark_store.name",read_only=True)
    computed_earnings = serializers.FloatField(read_only=True)

    class Meta:
        model  = DemandApplication
        fields = [
            "id", "demand_slot_id", "slot_title", "slot_date",
            "client_name", "dark_store_name",
            "rider_id", "status", "match_score",
            "applied_at", "confirmed_at", "rejection_reason",
            "check_in_at", "check_out_at",
            "orders_completed", "hours_worked",
            "earnings_credited", "computed_earnings", "earnings_paid_at",
            "created_at", "updated_at",
        ]


class ApplicationDecideSerializer(serializers.Serializer):
    action           = serializers.ChoiceField(choices=["CONFIRM", "REJECT", "SHORTLIST"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["action"] == "REJECT" and not data.get("rejection_reason", "").strip():
            raise serializers.ValidationError(
                {"rejection_reason": "Required when rejecting."}
            )
        return data


class CheckInSerializer(serializers.Serializer):
    latitude  = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)

    def validate_latitude(self, v):
        if v and not (-90 <= float(v) <= 90):
            raise serializers.ValidationError("Invalid latitude.")
        return v


class CheckOutSerializer(serializers.Serializer):
    latitude        = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude       = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    orders_completed = serializers.IntegerField(min_value=0, required=False, default=0)


class EarningsPayoutSerializer(serializers.Serializer):
    application_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1, max_length=100,
    )
    override_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, allow_null=True,
    )


# ── Matching results ──────────────────────────────────────────

class RiderMatchSerializer(serializers.Serializer):
    rider_id          = serializers.CharField()
    full_name         = serializers.CharField()
    distance_km       = serializers.FloatField()
    reliability_score = serializers.FloatField()
    total_completions = serializers.IntegerField()
    score             = serializers.FloatField()
    score_breakdown   = serializers.DictField()


# ── Fill rate & Analytics ─────────────────────────────────────

class FillRateSerializer(serializers.Serializer):
    slot_id          = serializers.UUIDField()
    title            = serializers.CharField()
    shift_date       = serializers.DateField()
    client_name      = serializers.CharField()
    riders_required  = serializers.IntegerField()
    riders_confirmed = serializers.IntegerField()
    riders_shown_up  = serializers.IntegerField()
    fill_rate        = serializers.FloatField()
    show_up_rate     = serializers.FloatField()
    status           = serializers.CharField()
