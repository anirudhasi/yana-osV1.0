"""
rider_service/core/tasks.py

Celery async tasks:
  - KYC verification simulation (background)
  - Notifications (WhatsApp / Firebase stub)
  - Digilocker/Karza integration stub
"""
import logging
import time
import random
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── KYC Verification (Simulated) ────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_kyc_verification(self, rider_id: str):
    """
    Simulates calling Digilocker / Karza API to verify rider documents.
    In production, replace with real API calls.

    Called after rider submits KYC details.
    """
    from rider_service.core.models import Rider, KYCVerificationLog

    logger.info("Starting KYC verification for rider %s", rider_id)

    try:
        rider = Rider.objects.get(id=rider_id)
    except Rider.DoesNotExist:
        logger.error("Rider %s not found for KYC verification", rider_id)
        return {"status": "error", "message": "Rider not found"}

    # Simulate processing delay (2-5 seconds)
    time.sleep(random.uniform(2, 5))

    # ── Aadhaar verification ──────────────────────────────────
    if rider.aadhaar_number and not rider.aadhaar_verified:
        aadhaar_result = _verify_aadhaar_mock(rider.aadhaar_number)
        if aadhaar_result["verified"]:
            rider.aadhaar_verified = True
            _log_kyc_event(rider, "AADHAAR_VERIFIED", provider="digilocker",
                           provider_response=aadhaar_result)

    # ── PAN verification ──────────────────────────────────────
    if rider.pan_number and not rider.pan_verified:
        pan_result = _verify_pan_mock(rider.pan_number)
        if pan_result["verified"]:
            rider.pan_verified = True
            _log_kyc_event(rider, "PAN_VERIFIED", provider="karza",
                           provider_response=pan_result)

    # ── DL verification ───────────────────────────────────────
    if rider.dl_number and not rider.dl_verified:
        dl_result = _verify_dl_mock(rider.dl_number)
        if dl_result["verified"]:
            rider.dl_verified = True
            _log_kyc_event(rider, "DL_VERIFIED", provider="karza",
                           provider_response=dl_result)

    # ── Bank verification ─────────────────────────────────────
    if rider.bank_account_number and rider.bank_ifsc and not rider.bank_verified:
        bank_result = _verify_bank_mock(rider.bank_account_number, rider.bank_ifsc)
        if bank_result["verified"]:
            rider.bank_verified = True
            _log_kyc_event(rider, "BANK_VERIFIED", provider="razorpay",
                           provider_response=bank_result)

    # ── Overall KYC decision ──────────────────────────────────
    all_verified = all([
        rider.aadhaar_verified,
        rider.pan_verified,
        rider.dl_verified,
        rider.bank_verified,
    ])

    old_kyc = rider.kyc_status

    if all_verified:
        rider.kyc_status = "UNDER_REVIEW"   # Queued for human review
        rider.save(update_fields=[
            "aadhaar_verified", "pan_verified", "dl_verified",
            "bank_verified", "kyc_status", "updated_at",
        ])
        _log_kyc_event(rider, "AUTO_VERIFICATION_PASSED",
                       old_status=old_kyc, new_status="UNDER_REVIEW",
                       notes="All documents auto-verified. Awaiting admin review.")
        logger.info("Rider %s KYC auto-verified — moved to UNDER_REVIEW", rider_id)
    else:
        failed = []
        if not rider.aadhaar_verified: failed.append("Aadhaar")
        if not rider.pan_verified:     failed.append("PAN")
        if not rider.dl_verified:      failed.append("Driving License")
        if not rider.bank_verified:    failed.append("Bank Account")

        rider.kyc_status = "REJECTED"
        rider.status     = "KYC_FAILED"
        rider.save(update_fields=["kyc_status", "status", "updated_at"])

        notes = f"Auto-verification failed for: {', '.join(failed)}"
        _log_kyc_event(rider, "AUTO_VERIFICATION_FAILED",
                       old_status=old_kyc, new_status="REJECTED", notes=notes)

        send_kyc_rejected_notification.delay(rider_id, notes)
        logger.warning("Rider %s KYC auto-verification failed: %s", rider_id, notes)

    return {"status": "completed", "rider_id": rider_id, "all_verified": all_verified}


def _log_kyc_event(rider, action: str, old_status: str = None, new_status: str = None,
                   provider: str = None, provider_response: dict = None, notes: str = None):
    from rider_service.core.models import KYCVerificationLog
    KYCVerificationLog.objects.create(
        rider=rider,
        action=action,
        old_status=old_status or rider.kyc_status,
        new_status=new_status or rider.kyc_status,
        provider=provider,
        provider_response=provider_response,
        notes=notes,
    )


# ── Mock API responses ────────────────────────────────────────

def _verify_aadhaar_mock(encrypted_aadhaar: str) -> dict:
    """Simulate Digilocker Aadhaar API call."""
    return {
        "verified": True,
        "provider": "digilocker",
        "ref_id":   f"DL{random.randint(100000,999999)}",
        "name_match": True,
        "dob_match":  True,
    }


def _verify_pan_mock(encrypted_pan: str) -> dict:
    """Simulate Karza PAN API call."""
    return {
        "verified": True,
        "provider": "karza",
        "ref_id":   f"KZ{random.randint(100000,999999)}",
        "name_match": True,
        "status": "VALID",
    }


def _verify_dl_mock(encrypted_dl: str) -> dict:
    """Simulate Sarathi DL API call via Karza."""
    return {
        "verified":   True,
        "provider":   "karza_sarathi",
        "ref_id":     f"DL{random.randint(100000,999999)}",
        "valid":      True,
        "vehicle_classes": ["LMV", "MCWG"],
    }


def _verify_bank_mock(account: str, ifsc: str) -> dict:
    """Simulate penny-drop bank account verification."""
    return {
        "verified":     True,
        "provider":     "razorpay_penny_drop",
        "account_name": "VERIFIED",
        "active":       True,
    }


# ─── Notification Tasks ───────────────────────────────────────

@shared_task
def send_kyc_approved_notification(rider_id: str):
    """Send WhatsApp / Firebase notification on KYC approval."""
    from rider_service.core.models import Rider
    try:
        rider = Rider.objects.get(id=rider_id)
        logger.info(
            "[NOTIFICATION] KYC approved for %s (%s). "
            "Message: 'Congratulations! Your KYC has been verified.'",
            rider.full_name, rider.phone,
        )
        # TODO: integrate with WhatsApp Business API or Firebase
    except Rider.DoesNotExist:
        logger.error("Rider %s not found for notification", rider_id)


@shared_task
def send_kyc_rejected_notification(rider_id: str, reason: str = ""):
    from rider_service.core.models import Rider
    try:
        rider = Rider.objects.get(id=rider_id)
        logger.warning(
            "[NOTIFICATION] KYC rejected for %s (%s). Reason: %s",
            rider.full_name, rider.phone, reason,
        )
    except Rider.DoesNotExist:
        logger.error("Rider %s not found for notification", rider_id)


@shared_task
def send_activation_notification(rider_id: str):
    from rider_service.core.models import Rider
    try:
        rider = Rider.objects.get(id=rider_id)
        logger.info(
            "[NOTIFICATION] Rider activated: %s (%s). "
            "Message: 'Welcome to Yana! You can now book a vehicle.'",
            rider.full_name, rider.phone,
        )
    except Rider.DoesNotExist:
        logger.error("Rider %s not found for notification", rider_id)


@shared_task
def trigger_kyc_verification_for_submitted():
    """
    Celery beat periodic task:
    Find all riders in KYC_PENDING and trigger verification.
    Runs every 10 minutes.
    """
    from rider_service.core.models import Rider
    riders = Rider.objects.filter(
        kyc_status="SUBMITTED",
        deleted_at__isnull=True,
    ).values_list("id", flat=True)

    count = 0
    for rider_id in riders:
        run_kyc_verification.delay(str(rider_id))
        count += 1

    logger.info("Queued KYC verification for %d riders", count)
    return {"queued": count}
