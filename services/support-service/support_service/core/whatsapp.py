"""
support_service/core/whatsapp.py
WhatsApp Business API integration — simulated in dev.
"""
import logging
from django.conf import settings
logger = logging.getLogger(__name__)

def send_whatsapp_message(phone: str, message: str, template: str = None) -> dict:
    """Send a WhatsApp message to a rider. Simulated in dev."""
    if settings.WHATSAPP_SIMULATE:
        logger.info("[WHATSAPP SIM] To %s: %s", phone, message[:100])
        return {"status": "simulated", "phone": phone}
    try:
        import httpx
        resp = httpx.post(
            f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
                     "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": f"91{phone}",
                  "type": "text", "text": {"body": message}},
            timeout=10.0,
        )
        return resp.json()
    except Exception as e:
        logger.error("WhatsApp send failed: %s", e)
        return {"status": "failed", "error": str(e)}


def send_ticket_created_whatsapp(ticket) -> None:
    """Notify rider of new ticket via WhatsApp."""
    try:
        rider = ticket.rider_id  # We'll use phone from cache or direct lookup
        msg = (
            f"✅ Your support request has been registered.\n"
            f"Ticket: *{ticket.ticket_number}*\n"
            f"Subject: {ticket.subject[:50]}\n"
            f"We'll respond within {_sla_label(ticket.priority)}.\n"
            f"Track: https://yana.in/support/{ticket.ticket_number}"
        )
        send_whatsapp_message(str(rider), msg)
    except Exception as e:
        logger.error("WhatsApp ticket notify failed: %s", e)


def _sla_label(priority: str) -> str:
    return {"LOW": "72 hours", "MEDIUM": "24 hours", "HIGH": "8 hours", "CRITICAL": "2 hours"}.get(priority, "24 hours")
