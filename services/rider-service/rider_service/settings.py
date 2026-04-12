"""
Yana OS — Rider Service Django Settings
"""
import os
import re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY   = config("SECRET_KEY", default="rider-dev-secret")
DEBUG        = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")

SERVICE_NAME = "rider-service"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "import_export",
    "rider_service.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF    = "rider_service.urls"
WSGI_APPLICATION = "rider_service.wsgi.application"

# ── Database ──────────────────────────────────────────────────
_db_url = config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os")
_m = re.match(r"postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _db_url)
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

# ── Redis / Celery ────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", "redis://redis:6379/1")

CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS":  {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT":  600,
    }
}

CELERY_BROKER_URL    = config("CELERY_BROKER_URL", "redis://redis:6379/2")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TIMEZONE          = "Asia/Kolkata"

# ── REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rider_service.core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "rider_service.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rider_service.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

# ── MinIO / S3 ────────────────────────────────────────────────
MINIO_ENDPOINT   = config("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = config("MINIO_ACCESS_KEY", "yana_minio")
MINIO_SECRET_KEY = config("MINIO_SECRET_KEY", "yana_minio_secret")
MINIO_BUCKET     = config("MINIO_BUCKET", "yana-documents")
MINIO_USE_SSL    = config("MINIO_USE_SSL", False, cast=bool)

# ── PII Encryption ────────────────────────────────────────────
PII_ENCRYPTION_KEY = config("PII_ENCRYPTION_KEY", "")

# ── JWT (shared with auth-service) ───────────────────────────
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)

# ── File Upload Limits ────────────────────────────────────────
MAX_UPLOAD_SIZE_MB   = 10
ALLOWED_DOCUMENT_TYPES = ["image/jpeg", "image/png", "application/pdf"]

# ── Spectacular ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "Yana OS — Rider Service",
    "DESCRIPTION": "Rider onboarding, KYC, and profile management",
    "VERSION":     "1.0.0",
}

# ── CORS ──────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ── Misc ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Asia/Kolkata"
USE_I18N      = True
USE_TZ        = True

# Shared DB: skip admin/sessions migrations — tables created by rider-service
MIGRATION_MODULES = {"admin": None, "sessions": None}

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]
    },
}]
