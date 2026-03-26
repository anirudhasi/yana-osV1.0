"""
auth_service/core/models.py

Auth-service owns the admin_users table.
Riders table is read-only here (for OTP login).
The Rider Service owns full rider data.
"""
import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


USER_ROLE_CHOICES = [
    ("SUPER_ADMIN",  "Super Admin"),
    ("CITY_ADMIN",   "City Admin"),
    ("HUB_OPS",      "Hub Ops"),
    ("SALES",        "Sales"),
    ("SUPPORT_AGENT","Support Agent"),
    ("VIEWER",       "Viewer"),
]

RIDER_STATUS_CHOICES = [
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


class AdminUser(models.Model):
    """
    Maps to: admin_users table (auth service owns this)
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email         = models.EmailField(max_length=255, unique=True)
    phone         = models.CharField(max_length=15, null=True, blank=True)
    full_name     = models.CharField(max_length=200)
    password_hash = models.TextField()
    role          = models.CharField(max_length=30, choices=USER_ROLE_CHOICES, default="VIEWER")
    city_id       = models.UUIDField(null=True, blank=True)
    hub_id        = models.UUIDField(null=True, blank=True)
    is_active     = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    deleted_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_users"
        indexes  = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def set_password(self, raw_password: str):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"{self.full_name} <{self.email}> [{self.role}]"


class Rider(models.Model):
    """
    Auth-service read-only view of riders (for OTP login).
    Rider service owns the full record.
    """
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone  = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=200)
    status = models.CharField(max_length=30, choices=RIDER_STATUS_CHOICES, default="APPLIED")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "riders"
        # No migrations for this model from auth-service —
        # Rider service manages the full table.
        managed = False

    def __str__(self):
        return f"Rider {self.phone}"

    @property
    def is_active(self):
        return self.deleted_at is None and self.status != "OFFBOARDED"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
