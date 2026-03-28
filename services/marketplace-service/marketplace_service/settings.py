"""
Yana OS — Marketplace Service Settings
Owns: demand_slots, demand_applications, client_dark_stores, clients, client_contracts
"""
import os, re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY    = config("SECRET_KEY", "marketplace-dev-secret")
DEBUG         = config("DEBUG", False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "*").split(",")
SERVICE_NAME  = "marketplace-service"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "marketplace_service.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF     = "marketplace_service.urls"
WSGI_APPLICATION = "marketplace_service.wsgi.application"

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
REDIS_URL = config("REDIS_URL", "redis://redis:6379/7")
CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS":  {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT":  600,
    }
}

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL     = config("CELERY_BROKER_URL", "redis://redis:6379/8")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/8")
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TIMEZONE           = "Asia/Kolkata"
CELERY_BEAT_SCHEDULER     = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "expire-demand-slots": {
        "task":     "marketplace_service.core.tasks.expire_old_demand_slots",
        "schedule": 3600,
    },
    "auto-confirm-applications": {
        "task":     "marketplace_service.core.tasks.auto_confirm_shortlisted_applications",
        "schedule": 900,
    },
    "compute-fill-rates": {
        "task":     "marketplace_service.core.tasks.compute_fill_rates",
        "schedule": 1800,
    },
}

# ── REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "marketplace_service.core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "marketplace_service.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "marketplace_service.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)

# ── Matching Engine ───────────────────────────────────────────
MATCH_RADIUS_KM          = config("MATCH_RADIUS_KM", 10, cast=int)
MIN_RELIABILITY_SCORE    = config("MIN_RELIABILITY_SCORE", 0.0, cast=float)
AUTO_CONFIRM_THRESHOLD   = config("AUTO_CONFIRM_THRESHOLD", 0.8, cast=float)

# ── Internal service URLs ─────────────────────────────────────
PAYMENTS_SERVICE_URL = config("PAYMENTS_SERVICE_URL", "http://payments-service:8004")
FLEET_SERVICE_URL    = config("FLEET_SERVICE_URL",    "http://fleet-service:8003")

# ── Spectacular ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "Yana OS — Marketplace Service",
    "DESCRIPTION": "Demand slots, rider matching, applications, attendance, earnings",
    "VERSION":     "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Asia/Kolkata"
USE_I18N      = True
USE_TZ        = True

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": []}}]
