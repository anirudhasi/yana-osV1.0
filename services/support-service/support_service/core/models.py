"""support_service/core/models.py"""
import uuid
from django.db import models

TICKET_STATUS = [
    ("OPEN","Open"), ("ASSIGNED","Assigned"), ("IN_PROGRESS","In Progress"),
    ("WAITING_RIDER","Waiting Rider"), ("RESOLVED","Resolved"),
    ("CLOSED","Closed"), ("ESCALATED","Escalated"),
]
TICKET_CATEGORY = [
    ("VEHICLE_ISSUE","Vehicle Issue"), ("PAYMENT_ISSUE","Payment Issue"),
    ("CUSTOMER_COMPLAINT","Customer Complaint"), ("APP_ISSUE","App Issue"),
    ("KYC_QUERY","KYC Query"), ("GENERAL","General"), ("OTHER","Other"),
]
TICKET_PRIORITY = [("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("CRITICAL","Critical")]
SENDER_TYPE    = [("RIDER","Rider"),("AGENT","Agent"),("SYSTEM","System")]


class Rider(models.Model):
    id = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    class Meta:
        db_table = "riders"
        managed  = False


class AdminUser(models.Model):
    id = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=30)
    class Meta:
        db_table = "admin_users"
        managed  = False


class SupportTicket(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number  = models.CharField(max_length=20, unique=True, blank=True)
    rider_id       = models.UUIDField(db_index=True)

    category     = models.CharField(max_length=30, choices=TICKET_CATEGORY)
    sub_category = models.CharField(max_length=100, null=True, blank=True)
    subject      = models.CharField(max_length=500)
    description  = models.TextField()
    attachments  = models.JSONField(default=list, blank=True)

    # References to other service objects
    vehicle_id       = models.UUIDField(null=True, blank=True)
    allotment_id     = models.UUIDField(null=True, blank=True)
    demand_slot_id   = models.UUIDField(null=True, blank=True)
    payment_txn_id   = models.UUIDField(null=True, blank=True)

    # Assignment
    assigned_to_id = models.UUIDField(null=True, blank=True)
    assigned_at    = models.DateTimeField(null=True, blank=True)

    # Status
    status   = models.CharField(max_length=20, choices=TICKET_STATUS,   default="OPEN")
    priority = models.CharField(max_length=10, choices=TICKET_PRIORITY,  default="MEDIUM")

    resolved_at      = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    rider_satisfaction = models.IntegerField(null=True, blank=True)  # 1-5

    # SLA
    sla_due_at   = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)

    # WhatsApp fallback
    whatsapp_thread_id = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_tickets"
        indexes  = [
            models.Index(fields=["rider_id",    "-created_at"]),
            models.Index(fields=["status",      "priority", "created_at"]),
            models.Index(fields=["assigned_to_id"]),
            models.Index(fields=["ticket_number"]),
        ]

    def __str__(self):
        return f"{self.ticket_number} [{self.status}] — {self.subject[:40]}"


class TicketMessage(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket      = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE)
    sender_rider_id = models.UUIDField(null=True, blank=True)
    sender_admin_id = models.UUIDField(null=True, blank=True)
    message     = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    is_internal = models.BooleanField(default=False)  # internal note — not visible to rider
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_messages"
        indexes  = [models.Index(fields=["ticket_id","created_at"])]

    def __str__(self):
        return f"Message by {self.sender_type} on ticket {self.ticket_id}"
