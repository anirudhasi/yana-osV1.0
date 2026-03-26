"""
rider_service/core/services.py

Business logic layer — keeps views thin.
All DB mutations happen here so they can be tested independently.
"""
import logging
import uuid
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import Rider, RiderDocument, RiderNominee, KYCVerificationLog, RiderStatusAudit
from .encryption import encrypt_pii
from .storage import upload_document
from .exceptions import KYCTransitionError, RiderStatusTransitionError, ValidationError

logger = logging.getLogger(__name__)


# ─── State machine definitions ────────────────────────────────

KYC_TRANSITIONS = {
    "PENDING":      ["SUBMITTED"],
    "SUBMITTED":    ["UNDER_REVIEW", "REJECTED"],
    "UNDER_REVIEW": ["VERIFIED", "REJECTED"],
    "REJECTED":     ["SUBMITTED"],     # Rider can resubmit
    "VERIFIED":     [],                # Terminal
}

RIDER_STATUS_TRANSITIONS = {
    "APPLIED":        ["DOCS_SUBMITTED", "OFFBOARDED"],
    "DOCS_SUBMITTED": ["KYC_PENDING",    "OFFBOARDED"],
    "KYC_PENDING":    ["KYC_FAILED",     "VERIFIED",  "OFFBOARDED"],
    "KYC_FAILED":     ["DOCS_SUBMITTED", "OFFBOARDED"],
    "VERIFIED":       ["TRAINING",       "OFFBOARDED"],
    "TRAINING":       ["ACTIVE",         "OFFBOARDED"],
    "ACTIVE":         ["SUSPENDED",      "OFFBOARDED"],
    "SUSPENDED":      ["ACTIVE",         "OFFBOARDED"],
    "OFFBOARDED":     [],
}


def _assert_kyc_transition(current: str, target: str):
    allowed = KYC_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise KYCTransitionError(current, target)


def _assert_rider_status_transition(current: str, target: str):
    allowed = RIDER_STATUS_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise RiderStatusTransitionError(current, target)


# ─── Audit helpers ────────────────────────────────────────────

def _log_rider_status_change(rider: Rider, old_status: str, new_status: str,
                              changed_by_id=None, reason: str = None):
    RiderStatusAudit.objects.create(
        rider=rider,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=changed_by_id,
        reason=reason,
    )


def _log_kyc_action(rider: Rider, action: str, old_status: str, new_status: str,
                    document: RiderDocument = None, performed_by_id=None,
                    provider: str = None, notes: str = None,
                    provider_response: dict = None, provider_ref_id: str = None):
    KYCVerificationLog.objects.create(
        rider=rider,
        document=document,
        action=action,
        performed_by_id=performed_by_id,
        provider=provider,
        provider_ref_id=provider_ref_id,
        provider_response=provider_response,
        old_status=old_status,
        new_status=new_status,
        notes=notes,
    )


# ─── Referral code generation ─────────────────────────────────

def _generate_referral_code(name: str) -> str:
    prefix = "".join(c for c in name.upper() if c.isalpha())[:3] or "YNA"
    suffix = str(uuid.uuid4().int)[:6]
    return f"{prefix}{suffix}"


# ─── 1. Create Rider ──────────────────────────────────────────

@transaction.atomic
def create_rider(validated_data: dict) -> Rider:
    """
    Creates a new rider record.
    Called by admin or self-registration.
    """
    phone = validated_data["phone"]

    if Rider.objects.filter(phone=phone, deleted_at__isnull=True).exists():
        raise ValidationError(f"Rider with phone {phone} already exists.")

    referral_code = _generate_referral_code(validated_data.get("full_name", "YNA"))
    # Ensure uniqueness
    while Rider.objects.filter(referral_code=referral_code).exists():
        referral_code = _generate_referral_code(validated_data.get("full_name", "YNA"))

    rider = Rider.objects.create(
        full_name=validated_data["full_name"],
        phone=phone,
        email=validated_data.get("email", ""),
        preferred_language=validated_data.get("preferred_language", "hi"),
        source=validated_data.get("source", "app"),
        referral_code=referral_code,
        status="APPLIED",
        kyc_status="PENDING",
    )

    _log_rider_status_change(rider, None, "APPLIED", reason="Initial registration")
    logger.info("Created rider %s (phone: %s)", rider.id, phone)
    return rider


# ─── 2. Update Rider Profile ──────────────────────────────────

@transaction.atomic
def update_rider_profile(rider: Rider, validated_data: dict) -> Rider:
    """Update non-sensitive profile fields."""
    updatable_fields = [
        "full_name", "email", "date_of_birth", "gender",
        "preferred_language", "address_line1", "address_line2",
        "city", "state", "pincode",
    ]
    changed = False
    for field in updatable_fields:
        if field in validated_data:
            setattr(rider, field, validated_data[field])
            changed = True

    if changed:
        rider.save(update_fields=updatable_fields + ["updated_at"])
        logger.info("Updated profile for rider %s", rider.id)

    return rider


# ─── 3. Upload KYC Document ───────────────────────────────────

@transaction.atomic
def upload_kyc_document(
    rider: Rider,
    file: InMemoryUploadedFile,
    document_type: str,
) -> RiderDocument:
    """
    Upload a document to MinIO and create/update the DB record.
    If a document of the same type already exists and was REJECTED,
    it creates a new version. Otherwise updates in place.
    """
    file_url, metadata = upload_document(file, str(rider.id), document_type)

    # Check for existing document of this type (non-verified)
    existing = RiderDocument.objects.filter(
        rider=rider,
        document_type=document_type,
    ).exclude(status="VERIFIED").first()

    if existing:
        # Re-upload: reset to PENDING
        existing.file_url         = file_url
        existing.file_name        = metadata["file_name"]
        existing.file_size_bytes  = metadata["file_size_bytes"]
        existing.mime_type        = metadata["mime_type"]
        existing.status           = "PENDING"
        existing.rejection_reason = None
        existing.verified_at      = None
        existing.save()
        doc = existing
        action = "RESUBMITTED"
    else:
        doc = RiderDocument.objects.create(
            rider=rider,
            document_type=document_type,
            file_url=file_url,
            file_name=metadata["file_name"],
            file_size_bytes=metadata["file_size_bytes"],
            mime_type=metadata["mime_type"],
            status="PENDING",
        )
        action = "UPLOADED"

    _log_kyc_action(
        rider=rider,
        action=action,
        old_status=rider.kyc_status,
        new_status=rider.kyc_status,
        document=doc,
        notes=f"Document type: {document_type}",
    )

    # Auto-advance rider status if first document upload
    if rider.status == "APPLIED":
        _advance_rider_to_docs_submitted(rider)

    logger.info("Uploaded %s for rider %s → doc %s", document_type, rider.id, doc.id)
    return doc


def _advance_rider_to_docs_submitted(rider: Rider):
    """Called when any document is uploaded for the first time."""
    try:
        _assert_rider_status_transition(rider.status, "DOCS_SUBMITTED")
        old = rider.status
        rider.status = "DOCS_SUBMITTED"
        rider.save(update_fields=["status", "updated_at"])
        _log_rider_status_change(rider, old, "DOCS_SUBMITTED", reason="First document uploaded")
    except RiderStatusTransitionError:
        pass  # Already past DOCS_SUBMITTED — that's fine


# ─── 4. Submit KYC Details (encrypted PII) ───────────────────

@transaction.atomic
def submit_kyc_details(rider: Rider, validated_data: dict) -> Rider:
    """
    Store encrypted PII fields and transition KYC to SUBMITTED.
    """
    field_map = {
        "aadhaar_number":     "aadhaar_number",
        "pan_number":         "pan_number",
        "dl_number":          "dl_number",
        "dl_expiry_date":     "dl_expiry_date",
        "dl_vehicle_class":   "dl_vehicle_class",
        "bank_account_number":"bank_account_number",
        "bank_ifsc":          "bank_ifsc",
        "bank_name":          "bank_name",
        "upi_id":             "upi_id",
    }

    ENCRYPT_FIELDS = {"aadhaar_number", "pan_number", "dl_number", "bank_account_number"}

    update_fields = []
    for key, model_field in field_map.items():
        value = validated_data.get(key)
        if value is not None:
            if key in ENCRYPT_FIELDS:
                value = encrypt_pii(str(value))
            setattr(rider, model_field, value)
            update_fields.append(model_field)

    old_kyc = rider.kyc_status

    if update_fields:
        # Transition KYC status
        if rider.kyc_status in ("PENDING", "REJECTED"):
            rider.kyc_status = "SUBMITTED"
            update_fields.append("kyc_status")

        update_fields.append("updated_at")
        rider.save(update_fields=update_fields)

        _log_kyc_action(
            rider=rider,
            action="SUBMITTED",
            old_status=old_kyc,
            new_status=rider.kyc_status,
            provider="rider_self",
            notes="Rider submitted KYC details",
        )

        # Advance rider status to KYC_PENDING if DOCS_SUBMITTED
        try:
            _assert_rider_status_transition(rider.status, "KYC_PENDING")
            old = rider.status
            rider.status = "KYC_PENDING"
            rider.save(update_fields=["status", "updated_at"])
            _log_rider_status_change(rider, old, "KYC_PENDING", reason="KYC details submitted")
        except RiderStatusTransitionError:
            pass

    return rider


# ─── 5. Upsert Nominee ────────────────────────────────────────

@transaction.atomic
def upsert_nominee(rider: Rider, validated_data: dict) -> RiderNominee:
    """Create or update primary nominee for a rider."""
    is_primary = validated_data.get("is_primary", True)

    # If setting as primary, demote existing primary
    if is_primary:
        RiderNominee.objects.filter(rider=rider, is_primary=True).update(is_primary=False)

    aadhaar = validated_data.get("aadhaar_number")
    if aadhaar:
        aadhaar = encrypt_pii(aadhaar)

    nominee, _ = RiderNominee.objects.update_or_create(
        rider=rider,
        relationship=validated_data["relationship"],
        defaults={
            "full_name":      validated_data["full_name"],
            "phone":          validated_data.get("phone"),
            "aadhaar_number": aadhaar,
            "is_primary":     is_primary,
        },
    )
    return nominee


# ─── 6. Admin Approve / Reject KYC ───────────────────────────

@transaction.atomic
def admin_kyc_decision(
    rider: Rider,
    action: str,
    admin_id: str,
    rejection_reason: str = None,
    notes: str = None,
) -> Rider:
    """
    Admin approves or rejects the overall rider KYC.
    action: 'APPROVE' | 'REJECT'
    """
    old_kyc    = rider.kyc_status
    old_status = rider.status

    if action == "APPROVE":
        _assert_kyc_transition(rider.kyc_status, "VERIFIED")

        rider.kyc_status        = "VERIFIED"
        rider.aadhaar_verified  = True
        rider.pan_verified      = True
        rider.dl_verified       = True
        rider.bank_verified     = True

        # Approve all pending/submitted documents
        RiderDocument.objects.filter(
            rider=rider,
            status__in=["PENDING", "SUBMITTED", "UNDER_REVIEW"],
        ).update(status="VERIFIED", verified_at=timezone.now(), verified_by_id=admin_id)

        # Advance rider status
        try:
            _assert_rider_status_transition(rider.status, "VERIFIED")
            rider.status = "VERIFIED"
            _log_rider_status_change(rider, old_status, "VERIFIED",
                                     changed_by_id=admin_id, reason="KYC approved by admin")
        except RiderStatusTransitionError:
            pass

        rider.save(update_fields=[
            "kyc_status", "aadhaar_verified", "pan_verified",
            "dl_verified", "bank_verified", "status", "updated_at",
        ])

        _log_kyc_action(
            rider=rider, action="VERIFIED",
            old_status=old_kyc, new_status="VERIFIED",
            performed_by_id=admin_id, provider="manual",
            notes=notes or "KYC approved by admin",
        )

        # Trigger Celery task: send activation notification
        from .tasks import send_kyc_approved_notification
        send_kyc_approved_notification.delay(str(rider.id))

    elif action == "REJECT":
        _assert_kyc_transition(rider.kyc_status, "REJECTED")

        rider.kyc_status = "REJECTED"

        try:
            _assert_rider_status_transition(rider.status, "KYC_FAILED")
            rider.status = "KYC_FAILED"
            _log_rider_status_change(rider, old_status, "KYC_FAILED",
                                     changed_by_id=admin_id, reason=rejection_reason)
        except RiderStatusTransitionError:
            pass

        rider.save(update_fields=["kyc_status", "status", "updated_at"])

        _log_kyc_action(
            rider=rider, action="REJECTED",
            old_status=old_kyc, new_status="REJECTED",
            performed_by_id=admin_id, provider="manual",
            notes=rejection_reason,
        )

        from .tasks import send_kyc_rejected_notification
        send_kyc_rejected_notification.delay(str(rider.id), rejection_reason)

    logger.info(
        "Admin %s %s KYC for rider %s (was: %s → now: %s)",
        admin_id, action, rider.id, old_kyc, rider.kyc_status,
    )
    return rider


@transaction.atomic
def admin_document_decision(
    document_id: str,
    action: str,
    admin_id: str,
    rejection_reason: str = None,
) -> RiderDocument:
    """Approve or reject a single document."""
    try:
        doc = RiderDocument.objects.select_related("rider").get(id=document_id)
    except RiderDocument.DoesNotExist:
        raise ValidationError(f"Document {document_id} not found.")

    if action == "APPROVE":
        doc.status      = "VERIFIED"
        doc.verified_at = timezone.now()
        doc.verified_by_id = admin_id
        doc.rejection_reason = None
        doc.save(update_fields=["status", "verified_at", "verified_by_id", "rejection_reason", "updated_at"])

        # Update rider's individual verification flag
        _update_rider_verification_flag(doc.rider, doc.document_type)

    elif action == "REJECT":
        doc.status           = "REJECTED"
        doc.rejection_reason = rejection_reason
        doc.verified_by_id   = admin_id
        doc.save(update_fields=["status", "rejection_reason", "verified_by_id", "updated_at"])

    _log_kyc_action(
        rider=doc.rider, action=action,
        old_status=doc.rider.kyc_status, new_status=doc.rider.kyc_status,
        document=doc, performed_by_id=admin_id, provider="manual",
        notes=rejection_reason,
    )
    return doc


def _update_rider_verification_flag(rider: Rider, document_type: str):
    flag_map = {
        "AADHAAR_FRONT": "aadhaar_verified",
        "AADHAAR_BACK":  "aadhaar_verified",
        "PAN":           "pan_verified",
        "DRIVING_LICENSE_FRONT": "dl_verified",
        "DRIVING_LICENSE_BACK":  "dl_verified",
        "BANK_PASSBOOK":    "bank_verified",
        "CANCELLED_CHEQUE": "bank_verified",
    }
    flag = flag_map.get(document_type)
    if flag:
        setattr(rider, flag, True)
        rider.save(update_fields=[flag, "updated_at"])


# ─── 7. Complete Training ─────────────────────────────────────

@transaction.atomic
def mark_training_completed(rider: Rider, admin_id: str = None) -> Rider:
    if rider.status != "VERIFIED":
        raise RiderStatusTransitionError(rider.status, "TRAINING_COMPLETE")

    old = rider.status
    rider.training_completed    = True
    rider.training_completed_at = timezone.now()
    rider.status                = "TRAINING"
    rider.save(update_fields=["training_completed", "training_completed_at", "status", "updated_at"])
    _log_rider_status_change(rider, old, "TRAINING",
                             changed_by_id=admin_id, reason="Training completed")
    return rider


# ─── 8. Activate Rider ───────────────────────────────────────

@transaction.atomic
def activate_rider(rider: Rider, admin_id: str) -> Rider:
    _assert_rider_status_transition(rider.status, "ACTIVE")
    old = rider.status
    rider.status       = "ACTIVE"
    rider.activated_at = timezone.now()
    rider.activated_by_id = admin_id
    rider.save(update_fields=["status", "activated_at", "activated_by_id", "updated_at"])
    _log_rider_status_change(rider, old, "ACTIVE",
                             changed_by_id=admin_id, reason="Activated by admin")

    from .tasks import send_activation_notification
    send_activation_notification.delay(str(rider.id))
    return rider
