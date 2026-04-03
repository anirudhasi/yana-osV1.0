"""support_service/core/tasks.py"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def send_ticket_created_notification(ticket_id: str):
    from support_service.core.models import SupportTicket
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        from support_service.core.whatsapp import send_ticket_created_whatsapp
        send_ticket_created_whatsapp(ticket)
    except Exception as e:
        logger.error("Ticket notification failed: %s", e)

@shared_task
def send_agent_reply_notification(ticket_id: str, message_preview: str):
    from support_service.core.models import SupportTicket
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        logger.info("[NOTIFY] WhatsApp to rider %s: Agent replied to %s", ticket.rider_id, ticket.ticket_number)
    except Exception as e:
        logger.error("Agent reply notify failed: %s", e)

@shared_task
def send_resolution_notification(ticket_id: str):
    from support_service.core.models import SupportTicket
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        logger.info("[NOTIFY] Ticket %s resolved — notifying rider %s", ticket.ticket_number, ticket.rider_id)
    except Exception as e:
        logger.error("Resolution notify failed: %s", e)

@shared_task
def check_sla_breaches():
    """Every 15 min: mark overdue tickets as SLA breached."""
    from support_service.core.models import SupportTicket
    now = timezone.now()
    breached = SupportTicket.objects.filter(
        sla_due_at__lt=now,
        sla_breached=False,
        status__in=["OPEN","ASSIGNED","IN_PROGRESS","WAITING_RIDER"],
    )
    count = breached.update(sla_breached=True)
    if count:
        logger.warning("SLA breached for %d tickets", count)
    return {"breached": count}

@shared_task
def auto_close_resolved_tickets():
    """Hourly: auto-close tickets resolved >48 hours ago without rider response."""
    from support_service.core.models import SupportTicket
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=48)
    closed = SupportTicket.objects.filter(status="RESOLVED", resolved_at__lt=cutoff).update(status="CLOSED")
    logger.info("Auto-closed %d resolved tickets", closed)
    return {"closed": closed}
