"""
Yana OS — Payments Service Settings
Owns: rider_wallets, wallet_ledger, payment_transactions, rent_schedule
"""
import os, re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY    = config("SECRET_KEY", "payments-dev-secret")
DEBUG         = config("DEBUG", False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "*").split(",")
SERVICE_NAME  = "payments-service"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "payments_service.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF     = "payments_service.urls"
WSGI_APPLICATION = "payments_service.wsgi.application"

# ── Database ──────────────────────────────────────────────────
_db = config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os")
_m  = re.match(r"postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _db)
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     _m.group(5) if _m else "yana_os",
        "USER":     _m.group(1) if _m else "yana_user",
        "PASSWORD": _m.group(2) if _m else "yana_secret",
        "HOST":     _m.group(3) if _m else "postgres",
        "PORT":     _m.group(4) if _m else "5432",
        "OPTIONS":  {"options": "-c search_path=public"},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Redis / Cache ─────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", "redis://redis:6379/5")
CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS":  {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT":  600,
    }
}

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL     = config("CELERY_BROKER_URL", "redis://redis:6379/6")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/6")
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TIMEZONE           = "Asia/Kolkata"
CELERY_BEAT_SCHEDULER     = "django_celery_beat.schedulers:DatabaseScheduler"

# Beat schedule — overridden by DB scheduler, but also defined here as defaults
CELERY_BEAT_SCHEDULE = {
    # Run daily rent deduction at 00:05 IST every day
    "daily-rent-deduction": {
        "task":     "payments_service.core.tasks.deduct_daily_rent",
        "schedule": 86400,           # 24 hours
        "options":  {"expires": 3600},
    },
    # Mark overdue schedules every hour
    "mark-overdue-rents": {
        "task":     "payments_service.core.tasks.mark_overdue_rent_schedules",
        "schedule": 3600,
    },
    # Process pending UPI autopay mandates every 6 hours
    "process-upi-autopay": {
        "task":     "payments_service.core.tasks.process_upi_autopay_mandates",
        "schedule": 21600,
    },
}

# ── REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "payments_service.core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "payments_service.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "payments_service.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)

# ── Razorpay ──────────────────────────────────────────────────
RAZORPAY_KEY_ID         = config("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET     = config("RAZORPAY_KEY_SECRET", "placeholder_secret")
RAZORPAY_WEBHOOK_SECRET = config("RAZORPAY_WEBHOOK_SECRET", "placeholder_webhook")
RAZORPAY_SIMULATE       = config("RAZORPAY_SIMULATE", True, cast=bool)

# ── Business Rules ────────────────────────────────────────────
OVERDUE_PENALTY_PER_DAY = config("OVERDUE_PENALTY_PER_DAY", 25, cast=int)   # INR
WALLET_OVERDRAFT_LIMIT  = config("WALLET_OVERDRAFT_LIMIT",  500, cast=int)   # INR

# ── Spectacular ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "Yana OS — Payments Service",
    "DESCRIPTION": "Wallet, ledger, rent schedules, and Razorpay integration",
    "VERSION":     "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Asia/Kolkata"
USE_I18N      = True
USE_TZ        = True

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": []}}]
