"""support_service/core/services.py"""
import uuid
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import SupportTicket, TicketMessage

logger = logging.getLogger(__name__)


def _generate_ticket_number() -> str:
    """YNA-2025-00001 format."""
    from django.db.models import Max
    year = timezone.now().year
    last = SupportTicket.objects.filter(
        ticket_number__startswith=f"YNA-{year}-"
    ).aggregate(Max("ticket_number"))["ticket_number__max"]
    if last:
        seq = int(last.split("-")[-1]) + 1
    else:
        seq = 1
    return f"YNA-{year}-{seq:05d}"


def _compute_sla_due(priority: str) -> timezone.datetime:
    sla_hours = settings.SLA_BY_PRIORITY.get(priority, settings.DEFAULT_SLA_HOURS)
    return timezone.now() + timedelta(hours=sla_hours)


@transaction.atomic
def create_ticket(rider_id: str, validated_data: dict) -> SupportTicket:
    ticket = SupportTicket.objects.create(
        rider_id      = rider_id,
        ticket_number = _generate_ticket_number(),
        sla_due_at    = _compute_sla_due(validated_data.get("priority", "MEDIUM")),
        **validated_data,
    )
    # Auto-open system message
    TicketMessage.objects.create(
        ticket      = ticket,
        sender_type = "SYSTEM",
        message     = f"Ticket {ticket.ticket_number} opened. Category: {ticket.get_category_display()}.",
        is_internal = False,
    )
    # WhatsApp notification (async)
    from .tasks import send_ticket_created_notification
    send_ticket_created_notification.delay(str(ticket.id))
    logger.info("Ticket created: %s (rider: %s)", ticket.ticket_number, rider_id)
    return ticket


@transaction.atomic
def add_message(ticket_id: str, sender_type: str, message: str,
                sender_rider_id=None, sender_admin_id=None,
                attachments=None, is_internal=False) -> TicketMessage:
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        raise ValueError(f"Ticket {ticket_id} not found.")

    if ticket.status == "CLOSED":
        raise ValueError("Cannot add messages to a closed ticket.")

    # Rider replying re-opens RESOLVED tickets
    if sender_type == "RIDER" and ticket.status == "RESOLVED":
        ticket.status = "IN_PROGRESS"
        ticket.resolved_at = None
        ticket.save(update_fields=["status","resolved_at","updated_at"])

    # Waiting for rider response → move to IN_PROGRESS
    if sender_type == "RIDER" and ticket.status == "WAITING_RIDER":
        ticket.status = "IN_PROGRESS"
        ticket.save(update_fields=["status","updated_at"])

    msg = TicketMessage.objects.create(
        ticket          = ticket,
        sender_type     = sender_type,
        sender_rider_id = sender_rider_id,
        sender_admin_id = sender_admin_id,
        message         = message,
        attachments     = attachments or [],
        is_internal     = is_internal,
    )

    # If agent replies, send WhatsApp to rider
    if sender_type == "AGENT" and not is_internal:
        from .tasks import send_agent_reply_notification
        send_agent_reply_notification.delay(str(ticket.id), message[:200])

    return msg


@transaction.atomic
def assign_ticket(ticket_id: str, agent_id: str) -> SupportTicket:
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        raise ValueError("Ticket not found.")
    ticket.assigned_to_id = agent_id
    ticket.assigned_at    = timezone.now()
    if ticket.status == "OPEN":
        ticket.status = "ASSIGNED"
    ticket.save(update_fields=["assigned_to_id","assigned_at","status","updated_at"])
    TicketMessage.objects.create(
        ticket=ticket, sender_type="SYSTEM", is_internal=True,
        message=f"Ticket assigned to agent {agent_id}.",
    )
    return ticket


@transaction.atomic
def resolve_ticket(ticket_id: str, agent_id: str, resolution_notes: str) -> SupportTicket:
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        raise ValueError("Ticket not found.")
    if ticket.status in ("RESOLVED","CLOSED"):
        raise ValueError(f"Ticket is already {ticket.status}.")
    ticket.status           = "RESOLVED"
    ticket.resolved_at      = timezone.now()
    ticket.resolution_notes = resolution_notes
    ticket.save(update_fields=["status","resolved_at","resolution_notes","updated_at"])
    TicketMessage.objects.create(
        ticket=ticket, sender_type="SYSTEM",
        message=f"Ticket resolved. Resolution: {resolution_notes[:100]}",
    )
    from .tasks import send_resolution_notification
    send_resolution_notification.delay(str(ticket.id))
    return ticket


@transaction.atomic
def escalate_ticket(ticket_id: str, agent_id: str, reason: str) -> SupportTicket:
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        raise ValueError("Ticket not found.")
    ticket.status   = "ESCALATED"
    ticket.priority = "HIGH" if ticket.priority not in ("HIGH","CRITICAL") else ticket.priority
    ticket.save(update_fields=["status","priority","updated_at"])
    TicketMessage.objects.create(
        ticket=ticket, sender_type="SYSTEM", is_internal=True,
        message=f"Escalated by agent {agent_id}. Reason: {reason}",
    )
    return ticket


@transaction.atomic
def rate_ticket(ticket_id: str, rider_id: str, rating: int) -> SupportTicket:
    try:
        ticket = SupportTicket.objects.get(id=ticket_id, rider_id=rider_id, status="RESOLVED")
    except SupportTicket.DoesNotExist:
        raise ValueError("Resolved ticket not found for this rider.")
    ticket.rider_satisfaction = rating
    ticket.save(update_fields=["rider_satisfaction","updated_at"])
    return ticket
