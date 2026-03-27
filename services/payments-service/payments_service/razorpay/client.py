"""
payments_service/razorpay/client.py

Razorpay integration wrapper.
Set RAZORPAY_SIMULATE=True in .env to run without real API keys.

Covers:
  - Order creation
  - Payment capture
  - Refunds
  - UPI AutoPay mandate creation
  - Webhook signature verification
"""
import hmac
import hashlib
import uuid
import logging
from decimal import Decimal
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def _paise(amount_inr: Decimal) -> int:
    """Convert INR Decimal to paise integer (Razorpay uses paise)."""
    return int(amount_inr * 100)


def _get_client():
    """Return a live Razorpay client (only used when SIMULATE=False)."""
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


# ── Order ─────────────────────────────────────────────────────

def create_order(amount_inr: Decimal, receipt: str, notes: dict = None) -> dict:
    """
    Create a Razorpay order for a rider payment.
    Returns order dict with id, amount, currency, status.
    """
    if settings.RAZORPAY_SIMULATE:
        order_id = f"order_sim_{uuid.uuid4().hex[:16]}"
        logger.info("[RAZORPAY SIM] Created order %s for ₹%s", order_id, amount_inr)
        return {
            "id":       order_id,
            "amount":   _paise(amount_inr),
            "currency": "INR",
            "receipt":  receipt,
            "status":   "created",
            "simulated": True,
        }

    client = _get_client()
    return client.order.create({
        "amount":   _paise(amount_inr),
        "currency": "INR",
        "receipt":  receipt,
        "notes":    notes or {},
        "payment_capture": 1,
    })


# ── Payment capture ───────────────────────────────────────────

def capture_payment(payment_id: str, amount_inr: Decimal) -> dict:
    """Capture an authorised payment."""
    if settings.RAZORPAY_SIMULATE:
        logger.info("[RAZORPAY SIM] Captured payment %s ₹%s", payment_id, amount_inr)
        return {
            "id":     payment_id,
            "amount": _paise(amount_inr),
            "status": "captured",
            "simulated": True,
        }
    return _get_client().payment.capture(payment_id, _paise(amount_inr))


def fetch_payment(payment_id: str) -> dict:
    """Fetch payment details from Razorpay."""
    if settings.RAZORPAY_SIMULATE:
        return {"id": payment_id, "status": "captured", "simulated": True}
    return _get_client().payment.fetch(payment_id)


# ── Refund ────────────────────────────────────────────────────

def create_refund(payment_id: str, amount_inr: Decimal, notes: dict = None) -> dict:
    """Issue a refund for a captured payment."""
    if settings.RAZORPAY_SIMULATE:
        refund_id = f"rfnd_sim_{uuid.uuid4().hex[:16]}"
        logger.info("[RAZORPAY SIM] Refund %s for payment %s ₹%s", refund_id, payment_id, amount_inr)
        return {
            "id":         refund_id,
            "payment_id": payment_id,
            "amount":     _paise(amount_inr),
            "status":     "processed",
            "simulated":  True,
        }
    return _get_client().payment.refund(payment_id, {
        "amount": _paise(amount_inr),
        "notes":  notes or {},
    })


# ── UPI AutoPay Mandate ───────────────────────────────────────

def create_upi_autopay_mandate(
    rider_id: str,
    upi_id: str,
    max_amount_inr: Decimal,
    rider_name: str,
    rider_phone: str,
) -> dict:
    """
    Create a Razorpay recurring UPI AutoPay mandate.
    Used for automatic daily rent collection.
    """
    if settings.RAZORPAY_SIMULATE:
        mandate_id  = f"mandate_sim_{uuid.uuid4().hex[:16]}"
        customer_id = f"cust_sim_{uuid.uuid4().hex[:12]}"
        logger.info("[RAZORPAY SIM] UPI AutoPay mandate %s for rider %s", mandate_id, rider_id)
        return {
            "mandate_id":  mandate_id,
            "customer_id": customer_id,
            "upi_id":      upi_id,
            "max_amount":  _paise(max_amount_inr),
            "status":      "created",
            "simulated":   True,
        }

    client = _get_client()

    # Step 1: Create / fetch Razorpay customer
    customer = client.customer.create({
        "name":    rider_name,
        "contact": f"+91{rider_phone}",
        "notes":   {"rider_id": str(rider_id)},
    })

    # Step 2: Create recurring mandate
    # Razorpay recurring payments with UPI
    subscription = client.subscription.create({
        "plan_id":         "plan_placeholder",   # replace with real plan_id in prod
        "customer_notify": 1,
        "quantity":        1,
        "total_count":     365,   # 1 year
        "notes":           {"rider_id": str(rider_id), "upi_id": upi_id},
    })

    return {
        "mandate_id":  subscription["id"],
        "customer_id": customer["id"],
        "upi_id":      upi_id,
        "status":      subscription["status"],
    }


def charge_upi_autopay(mandate_id: str, amount_inr: Decimal, description: str) -> dict:
    """Execute a UPI AutoPay debit against an active mandate."""
    if settings.RAZORPAY_SIMULATE:
        payment_id = f"pay_sim_{uuid.uuid4().hex[:16]}"
        logger.info("[RAZORPAY SIM] AutoPay ₹%s via mandate %s", amount_inr, mandate_id)
        return {
            "payment_id": payment_id,
            "amount":     _paise(amount_inr),
            "status":     "captured",
            "simulated":  True,
        }

    client   = _get_client()
    invoice  = client.invoice.create({
        "type":         "invoice",
        "description":  description,
        "subscription_id": mandate_id,
        "amount":       _paise(amount_inr),
        "currency":     "INR",
    })
    return {"payment_id": invoice.get("id"), "status": invoice.get("status")}


# ── Webhook verification ──────────────────────────────────────

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook signature using HMAC-SHA256.
    Must be called before processing any webhook.
    """
    if settings.RAZORPAY_SIMULATE:
        return True   # Skip verification in simulation mode

    secret  = settings.RAZORPAY_WEBHOOK_SECRET.encode()
    digest  = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
