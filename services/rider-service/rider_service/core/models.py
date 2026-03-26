"""
rider_service/core/models.py

Owns: riders, rider_documents, rider_nominees,
      kyc_verification_logs, rider_status_audit
Also references: admin_users (unmanaged), fleet_hubs (unmanaged)
"""
import uuid
from django.db import models


# ── Enums as choices ──────────────────────────────────────────

RIDER_STATUS = [
    ("APPLIED",        "Applied"),
    ("DOCS_SUBMITTED", "Documents Submitted"),
    ("KYC_PENDING",    "KYC Pending"),
    ("KYC_FAILED",     "KYC Failed"),
    ("VERIFIED",       "Verified"),
    ("TRAINING",       "Training"),
    ("ACTIVE",         "Active"),
    ("SUSPENDED",      "Suspended"),
    ("OFFBOARDED",     "Offboarded"),
]

KYC_STATUS = [
    ("PENDING",      "Pending"),
    ("SUBMITTED",    "Submitted"),
    ("UNDER_REVIEW", "Under Review"),
    ("VERIFIED",     "Verified"),
    ("REJECTED",     "Rejected"),
]

DOCUMENT_TYPE = [
    ("AADHAAR_FRONT",         "Aadhaar Front"),
    ("AADHAAR_BACK",          "Aadhaar Back"),
    ("PAN",                   "PAN Card"),
    ("DRIVING_LICENSE_FRONT", "Driving License Front"),
    ("DRIVING_LICENSE_BACK",  "Driving License Back"),
    ("BANK_PASSBOOK",         "Bank Passbook"),
    ("CANCELLED_CHEQUE",      "Cancelled Cheque"),
    ("PROFILE_PHOTO",         "Profile Photo"),
    ("OTHER",                 "Other"),
]


# ── Unmanaged stubs (owned by other services) ─────────────────

class FleetHub(models.Model):
    id   = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "fleet_hubs"
        managed  = False


class AdminUser(models.Model):
    id        = models.UUIDField(primary_key=True)
    full_name = models.CharField(max_length=200)
    email     = models.EmailField()

    class Meta:
        db_table = "admin_users"
        managed  = False


# ── Core Models ───────────────────────────────────────────────

class Rider(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    full_name          = models.CharField(max_length=200)
    phone              = models.CharField(max_length=15, unique=True)
    email              = models.EmailField(null=True, blank=True)
    date_of_birth      = models.DateField(null=True, blank=True)
    gender             = models.CharField(max_length=10, null=True, blank=True)
    profile_photo_url  = models.TextField(null=True, blank=True)
    preferred_language = models.CharField(max_length=20, default="hi")

    # Address
    address_line1 = models.TextField(null=True, blank=True)
    address_line2 = models.TextField(null=True, blank=True)
    city          = models.CharField(max_length=100, null=True, blank=True)
    state         = models.CharField(max_length=100, null=True, blank=True)
    pincode       = models.CharField(max_length=10, null=True, blank=True)
    latitude      = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude     = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    # Government IDs (stored encrypted by service layer)
    aadhaar_number = models.CharField(max_length=500, null=True, blank=True)
    pan_number     = models.CharField(max_length=500, null=True, blank=True)
    dl_number      = models.CharField(max_length=500, null=True, blank=True)
    dl_expiry_date    = models.DateField(null=True, blank=True)
    dl_vehicle_class  = models.CharField(max_length=50, null=True, blank=True)

    # Bank details (stored encrypted)
    bank_account_number = models.CharField(max_length=500, null=True, blank=True)
    bank_ifsc           = models.CharField(max_length=20, null=True, blank=True)
    bank_name           = models.CharField(max_length=200, null=True, blank=True)
    upi_id              = models.CharField(max_length=200, null=True, blank=True)

    # Status
    status     = models.CharField(max_length=30, choices=RIDER_STATUS, default="APPLIED")
    kyc_status = models.CharField(max_length=30, choices=KYC_STATUS,   default="PENDING")

    # Verification flags
    aadhaar_verified = models.BooleanField(default=False)
    pan_verified     = models.BooleanField(default=False)
    dl_verified      = models.BooleanField(default=False)
    bank_verified    = models.BooleanField(default=False)

    # Hub
    hub_id  = models.UUIDField(null=True, blank=True)
    city_id = models.UUIDField(null=True, blank=True)

    # Onboarding
    training_completed    = models.BooleanField(default=False)
    training_completed_at = models.DateTimeField(null=True, blank=True)
    activated_at          = models.DateTimeField(null=True, blank=True)
    activated_by_id       = models.UUIDField(null=True, blank=True)

    # AI score (Phase 3)
    reliability_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    # Referral
    referral_code  = models.CharField(max_length=20, unique=True, null=True, blank=True)
    referred_by_id = models.UUIDField(null=True, blank=True)
    source         = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "riders"
        indexes  = [
            models.Index(fields=["phone"]),
            models.Index(fields=["status"]),
            models.Index(fields=["hub_id"]),
            models.Index(fields=["city_id"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class RiderNominee(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider        = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="nominees")
    full_name    = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50)
    phone        = models.CharField(max_length=15, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=500, null=True, blank=True)  # encrypted
    is_primary   = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rider_nominees"
        indexes  = [models.Index(fields=["rider_id"])]

    def __str__(self):
        return f"{self.full_name} ({self.relationship}) → {self.rider}"


class RiderDocument(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider         = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE)
    file_url      = models.TextField()
    file_name     = models.CharField(max_length=500, null=True, blank=True)
    file_size_bytes = models.IntegerField(null=True, blank=True)
    mime_type     = models.CharField(max_length=100, null=True, blank=True)
    status        = models.CharField(max_length=30, choices=KYC_STATUS, default="PENDING")
    verified_by_id  = models.UUIDField(null=True, blank=True)
    verified_at   = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    external_ref_id  = models.TextField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rider_documents"
        indexes  = [
            models.Index(fields=["rider_id"]),
            models.Index(fields=["document_type", "status"]),
        ]

    def __str__(self):
        return f"{self.document_type} — {self.rider} [{self.status}]"


class KYCVerificationLog(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider       = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="kyc_logs")
    document    = models.ForeignKey(RiderDocument, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="verification_logs")
    action      = models.CharField(max_length=50)       # SUBMITTED, VERIFIED, REJECTED, RETRY
    performed_by_id = models.UUIDField(null=True, blank=True)  # NULL = API/auto
    provider        = models.CharField(max_length=50, null=True, blank=True)  # digilocker, karza, manual
    provider_ref_id = models.TextField(null=True, blank=True)
    provider_response = models.JSONField(null=True, blank=True)
    old_status  = models.CharField(max_length=30, null=True, blank=True)
    new_status  = models.CharField(max_length=30)
    notes       = models.TextField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kyc_verification_logs"
        indexes  = [models.Index(fields=["rider_id", "-created_at"])]

    def __str__(self):
        return f"{self.action}: {self.old_status} → {self.new_status} [{self.rider}]"


class RiderStatusAudit(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider       = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="status_audit")
    old_status  = models.CharField(max_length=30, null=True, blank=True)
    new_status  = models.CharField(max_length=30)
    changed_by_id = models.UUIDField(null=True, blank=True)  # NULL = system
    reason      = models.TextField(null=True, blank=True)
    metadata    = models.JSONField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rider_status_audit"
        indexes  = [models.Index(fields=["rider_id", "-created_at"])]
