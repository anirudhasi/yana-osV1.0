"""
Yana OS — Fleet Service Settings
Owns: vehicles, vehicle_allotments, vehicle_gps_telemetry,
      fleet_hubs, cities, maintenance_alerts
"""
import os, re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY    = config("SECRET_KEY", "fleet-dev-secret")
DEBUG         = config("DEBUG", False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "*").split(",")
SERVICE_NAME  = "fleet-service"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "fleet_service.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF     = "fleet_service.urls"
WSGI_APPLICATION = "fleet_service.wsgi.application"

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

# ── Redis ─────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", "redis://redis:6379/3")
CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS":  {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT":  600,
    }
}

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL     = config("CELERY_BROKER_URL", "redis://redis:6379/4")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/4")
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TIMEZONE           = "Asia/Kolkata"
CELERY_BEAT_SCHEDULE = {
    "check-maintenance-alerts": {
        "task":     "fleet_service.core.tasks.check_maintenance_alerts",
        "schedule": 3600,   # every hour
    },
    "refresh-hub-utilization": {
        "task":     "fleet_service.core.tasks.refresh_hub_utilization_cache",
        "schedule": 900,    # every 15 min
    },
}

# ── REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "fleet_service.core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "fleet_service.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "fleet_service.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)

# ── GPS Telemetry ─────────────────────────────────────────────
GPS_BATCH_SIZE            = config("GPS_BATCH_SIZE", 50, cast=int)
GPS_FLUSH_INTERVAL_SECONDS = config("GPS_FLUSH_INTERVAL_SECONDS", 5, cast=int)

# ── Spectacular ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "Yana OS — Fleet Service",
    "DESCRIPTION": "Vehicle management, allotment engine, GPS telemetry",
    "VERSION":     "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Asia/Kolkata"
USE_I18N      = True
USE_TZ        = True

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": []}}]
