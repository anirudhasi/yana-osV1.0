"""support_service/core/serializers.py"""
from rest_framework import serializers
from .models import SupportTicket, TicketMessage

class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TicketMessage
        fields = ["id","sender_type","sender_rider_id","sender_admin_id",
                  "message","attachments","is_internal","created_at"]

class SupportTicketSerializer(serializers.ModelSerializer):
    messages       = TicketMessageSerializer(many=True, read_only=True)
    sla_status     = serializers.SerializerMethodField()
    class Meta:
        model  = SupportTicket
        fields = [
            "id","ticket_number","rider_id","category","sub_category",
            "subject","description","attachments",
            "vehicle_id","allotment_id","demand_slot_id","payment_txn_id",
            "assigned_to_id","assigned_at","status","priority",
            "resolved_at","resolution_notes","rider_satisfaction",
            "sla_due_at","sla_breached","whatsapp_thread_id",
            "sla_status","messages","created_at","updated_at",
        ]
    def get_sla_status(self, obj):
        from django.utils import timezone
        if not obj.sla_due_at: return "NO_SLA"
        now = timezone.now()
        if obj.status in ("RESOLVED","CLOSED"): return "MET"
        if obj.sla_breached or now > obj.sla_due_at: return "BREACHED"
        remaining = (obj.sla_due_at - now).total_seconds() / 3600
        if remaining < 1: return "AT_RISK"
        return "ON_TRACK"

class CreateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SupportTicket
        fields = ["category","sub_category","subject","description","attachments",
                  "vehicle_id","allotment_id","demand_slot_id","payment_txn_id","priority"]

class AddMessageSerializer(serializers.Serializer):
    message     = serializers.CharField(min_length=1)
    attachments = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    is_internal = serializers.BooleanField(default=False)

class AssignTicketSerializer(serializers.Serializer):
    agent_id = serializers.UUIDField()

class ResolveTicketSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(min_length=5)

class RatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)

class BulkAssignSerializer(serializers.Serializer):
    ticket_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=50)
    agent_id   = serializers.UUIDField()
