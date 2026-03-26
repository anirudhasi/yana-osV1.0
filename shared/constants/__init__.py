# shared/constants/__init__.py
# ─────────────────────────────────────────────────────────────
# Yana OS — Shared Constants
# These mirror the PostgreSQL ENUM types exactly.
# ─────────────────────────────────────────────────────────────

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

KYC_STATUS_CHOICES = [
    ("PENDING",       "Pending"),
    ("SUBMITTED",     "Submitted"),
    ("UNDER_REVIEW",  "Under Review"),
    ("VERIFIED",      "Verified"),
    ("REJECTED",      "Rejected"),
]

DOCUMENT_TYPE_CHOICES = [
    ("AADHAAR_FRONT",           "Aadhaar Front"),
    ("AADHAAR_BACK",            "Aadhaar Back"),
    ("PAN",                     "PAN Card"),
    ("DRIVING_LICENSE_FRONT",   "Driving License Front"),
    ("DRIVING_LICENSE_BACK",    "Driving License Back"),
    ("BANK_PASSBOOK",           "Bank Passbook"),
    ("CANCELLED_CHEQUE",        "Cancelled Cheque"),
    ("PROFILE_PHOTO",           "Profile Photo"),
    ("OTHER",                   "Other"),
]

USER_ROLE_CHOICES = [
    ("SUPER_ADMIN", "Super Admin"),
    ("CITY_ADMIN",  "City Admin"),
    ("HUB_OPS",     "Hub Ops"),
    ("SALES",       "Sales"),
    ("SUPPORT_AGENT","Support Agent"),
    ("VIEWER",      "Viewer"),
]

VEHICLE_STATUS_CHOICES = [
    ("AVAILABLE",    "Available"),
    ("ALLOCATED",    "Allocated"),
    ("MAINTENANCE",  "Maintenance"),
    ("RETIRED",      "Retired"),
    ("LOST",         "Lost"),
]

TICKET_STATUS_CHOICES = [
    ("OPEN",           "Open"),
    ("ASSIGNED",       "Assigned"),
    ("IN_PROGRESS",    "In Progress"),
    ("WAITING_RIDER",  "Waiting Rider"),
    ("RESOLVED",       "Resolved"),
    ("CLOSED",         "Closed"),
    ("ESCALATED",      "Escalated"),
]

OTP_EXPIRY_SECONDS = 300       # 5 minutes
OTP_MAX_ATTEMPTS   = 3
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS   = 30
