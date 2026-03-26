"""
rider_service/core/serializers.py

All DRF serializers for the rider onboarding flow.
"""
import re
from rest_framework import serializers
from .models import Rider, RiderDocument, RiderNominee, KYCVerificationLog
from .encryption import mask_aadhaar, mask_account, decrypt_pii


# ─── Helpers ──────────────────────────────────────────────────

def validate_indian_phone(value: str) -> str:
    clean = re.sub(r"[\s\-\(\)]", "", value)
    if clean.startswith("+91"):
        clean = clean[3:]
    if not re.fullmatch(r"[6-9]\d{9}", clean):
        raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
    return clean


def validate_aadhaar(value: str) -> str:
    clean = re.sub(r"\s", "", value)
    if not re.fullmatch(r"\d{12}", clean):
        raise serializers.ValidationError("Aadhaar must be 12 digits.")
    return clean


def validate_pan(value: str) -> str:
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", value.upper().strip()):
        raise serializers.ValidationError("PAN must be in format ABCDE1234F.")
    return value.upper().strip()


def validate_ifsc(value: str) -> str:
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value.upper().strip()):
        raise serializers.ValidationError("Enter a valid IFSC code (e.g. SBIN0001234).")
    return value.upper().strip()


# ─── Create Rider ─────────────────────────────────────────────

class CreateRiderSerializer(serializers.Serializer):
    full_name          = serializers.CharField(max_length=200)
    phone              = serializers.CharField(max_length=15)
    email              = serializers.EmailField(required=False, allow_blank=True)
    preferred_language = serializers.ChoiceField(
        choices=["hi", "en", "mr", "bn", "ta", "te", "kn"],
        default="hi",
    )
    source = serializers.CharField(max_length=50, required=False, default="app")

    def validate_phone(self, value):
        return validate_indian_phone(value)

    def validate_phone_unique(self, phone):
        if Rider.objects.filter(phone=phone, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("A rider with this phone already exists.")
        return phone

    def validate(self, data):
        self.validate_phone_unique(data["phone"])
        return data


# ─── Update Profile ───────────────────────────────────────────

class UpdateRiderProfileSerializer(serializers.Serializer):
    full_name     = serializers.CharField(max_length=200,  required=False)
    email         = serializers.EmailField(required=False,  allow_blank=True)
    date_of_birth = serializers.DateField(required=False)
    gender        = serializers.ChoiceField(
        choices=["MALE", "FEMALE", "OTHER"],
        required=False,
    )
    preferred_language = serializers.ChoiceField(
        choices=["hi", "en", "mr", "bn", "ta", "te", "kn"],
        required=False,
    )
    address_line1 = serializers.CharField(required=False, allow_blank=True)
    address_line2 = serializers.CharField(required=False, allow_blank=True)
    city          = serializers.CharField(max_length=100, required=False)
    state         = serializers.CharField(max_length=100, required=False)
    pincode       = serializers.CharField(max_length=10,  required=False)


# ─── KYC Details ──────────────────────────────────────────────

class SubmitKYCDetailsSerializer(serializers.Serializer):
    """Sensitive fields — encrypted before storage."""

    # Aadhaar
    aadhaar_number = serializers.CharField(max_length=12, required=False)

    # PAN
    pan_number = serializers.CharField(max_length=10, required=False)

    # Driving License
    dl_number       = serializers.CharField(max_length=20, required=False)
    dl_expiry_date  = serializers.DateField(required=False)
    dl_vehicle_class = serializers.CharField(max_length=50, required=False)

    # Bank
    bank_account_number = serializers.CharField(max_length=20, required=False)
    bank_ifsc           = serializers.CharField(max_length=11, required=False)
    bank_name           = serializers.CharField(max_length=200, required=False)
    upi_id              = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_aadhaar_number(self, value):
        return validate_aadhaar(value)

    def validate_pan_number(self, value):
        return validate_pan(value)

    def validate_bank_ifsc(self, value):
        return validate_ifsc(value)

    def validate(self, data):
        # At least one field must be provided
        if not any(data.values()):
            raise serializers.ValidationError("Provide at least one KYC field.")
        return data


# ─── Nominee ──────────────────────────────────────────────────

class NomineeSerializer(serializers.Serializer):
    full_name    = serializers.CharField(max_length=200)
    relationship = serializers.ChoiceField(
        choices=["SPOUSE", "PARENT", "SIBLING", "CHILD", "OTHER"]
    )
    phone          = serializers.CharField(max_length=15, required=False)
    aadhaar_number = serializers.CharField(max_length=12, required=False)
    is_primary     = serializers.BooleanField(default=True)

    def validate_phone(self, value):
        if value:
            return validate_indian_phone(value)
        return value

    def validate_aadhaar_number(self, value):
        if value:
            return validate_aadhaar(value)
        return value


# ─── Admin KYC Decision ───────────────────────────────────────

class AdminKYCDecisionSerializer(serializers.Serializer):
    action           = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    notes            = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["action"] == "REJECT" and not data.get("rejection_reason", "").strip():
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting KYC."}
            )
        return data


class DocumentKYCDecisionSerializer(serializers.Serializer):
    document_id      = serializers.UUIDField()
    action           = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["action"] == "REJECT" and not data.get("rejection_reason", "").strip():
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting."}
            )
        return data


# ─── Response Serializers ─────────────────────────────────────

class NomineeResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RiderNominee
        fields = ["id", "full_name", "relationship", "phone", "is_primary"]


class DocumentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RiderDocument
        fields = [
            "id", "document_type", "file_url", "file_name",
            "file_size_bytes", "mime_type", "status",
            "verified_at", "rejection_reason", "created_at",
        ]


class RiderProfileSerializer(serializers.ModelSerializer):
    """
    Full profile — masks sensitive fields.
    Only admin can see unmasked; rider sees masked.
    """
    aadhaar_masked      = serializers.SerializerMethodField()
    bank_account_masked = serializers.SerializerMethodField()
    documents           = DocumentResponseSerializer(many=True, read_only=True)
    nominees            = NomineeResponseSerializer(many=True, read_only=True)

    class Meta:
        model  = Rider
        fields = [
            "id", "full_name", "phone", "email",
            "date_of_birth", "gender", "profile_photo_url",
            "preferred_language",
            "address_line1", "address_line2", "city", "state", "pincode",
            "latitude", "longitude",
            # Masked PII
            "aadhaar_masked", "bank_account_masked",
            "pan_number",       # shown as plain (masked by caller if needed)
            "dl_number", "dl_expiry_date", "dl_vehicle_class",
            "bank_ifsc", "bank_name", "upi_id",
            # Flags
            "aadhaar_verified", "pan_verified", "dl_verified", "bank_verified",
            # Status
            "status", "kyc_status",
            "hub_id", "city_id",
            "training_completed", "training_completed_at",
            "activated_at",
            "reliability_score",
            "referral_code", "source",
            "created_at", "updated_at",
            # Relations
            "documents", "nominees",
        ]

    def get_aadhaar_masked(self, obj):
        return mask_aadhaar(obj.aadhaar_number)

    def get_bank_account_masked(self, obj):
        return mask_account(obj.bank_account_number)


class RiderListSerializer(serializers.ModelSerializer):
    """Lightweight list view."""
    class Meta:
        model  = Rider
        fields = [
            "id", "full_name", "phone", "email",
            "status", "kyc_status",
            "city", "state",
            "hub_id", "city_id",
            "created_at",
        ]


class OnboardingStatusSerializer(serializers.ModelSerializer):
    """Returns current onboarding progress for the rider app."""
    documents_uploaded   = serializers.SerializerMethodField()
    pending_documents    = serializers.SerializerMethodField()
    onboarding_steps     = serializers.SerializerMethodField()

    class Meta:
        model  = Rider
        fields = [
            "id", "full_name", "phone",
            "status", "kyc_status",
            "aadhaar_verified", "pan_verified",
            "dl_verified", "bank_verified",
            "training_completed",
            "documents_uploaded",
            "pending_documents",
            "onboarding_steps",
        ]

    def get_documents_uploaded(self, obj):
        return obj.documents.values_list("document_type", flat=True)

    def get_pending_documents(self, obj):
        required = {
            "AADHAAR_FRONT", "AADHAAR_BACK",
            "PAN",
            "DRIVING_LICENSE_FRONT",
            "BANK_PASSBOOK",
        }
        uploaded = set(obj.documents.filter(
            status__in=["PENDING", "SUBMITTED", "UNDER_REVIEW", "VERIFIED"]
        ).values_list("document_type", flat=True))
        return list(required - uploaded)

    def get_onboarding_steps(self, obj):
        return [
            {
                "step":      1,
                "title":     "Create Account",
                "completed": True,
            },
            {
                "step":      2,
                "title":     "Upload Documents",
                "completed": obj.documents.filter(status__in=["SUBMITTED", "UNDER_REVIEW", "VERIFIED"]).exists(),
            },
            {
                "step":      3,
                "title":     "KYC Verification",
                "completed": obj.kyc_status == "VERIFIED",
            },
            {
                "step":      4,
                "title":     "Complete Training",
                "completed": obj.training_completed,
            },
            {
                "step":      5,
                "title":     "Account Activation",
                "completed": obj.status == "ACTIVE",
            },
        ]


class KYCLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KYCVerificationLog
        fields = [
            "id", "action", "provider",
            "old_status", "new_status",
            "notes", "created_at",
        ]
