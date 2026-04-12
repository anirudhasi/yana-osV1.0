"""
Yana OS — Auth Service Django Settings
"""
import os
from datetime import timedelta
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-change-in-prod")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")

SERVICE_NAME = "auth-service"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "import_export",
    "auth_service.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "auth_service.urls"
WSGI_APPLICATION = "auth_service.wsgi.application"

# ── Database ──────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     config("DATABASE_URL", "").split("/")[-1] or "yana_os",
        "USER":     "yana_user",
        "PASSWORD": "yana_secret",
        "HOST":     config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os").split("@")[1].split(":")[0] if "@" in config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os") else "postgres",
        "PORT":     "5432",
        "OPTIONS": {"options": "-c search_path=public"},
    }
}

# Parse DATABASE_URL properly
_db_url = config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os")
if _db_url.startswith("postgres://"):
    import re
    _m = re.match(r"postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _db_url)
    if _m:
        DATABASES["default"]["USER"]     = _m.group(1)
        DATABASES["default"]["PASSWORD"] = _m.group(2)
        DATABASES["default"]["HOST"]     = _m.group(3)
        DATABASES["default"]["PORT"]     = _m.group(4)
        DATABASES["default"]["NAME"]     = _m.group(5)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Redis / Cache ─────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", "redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS":  {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT":  300,
    }
}

# ── REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "auth_service.core.exceptions.custom_exception_handler",
}

# ── JWT ───────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=config("JWT_ACCESS_EXPIRES_MINUTES", 60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_EXPIRES_DAYS", 30, cast=int)),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM":     "HS256",
    "SIGNING_KEY":   config("JWT_SECRET_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ── OTP ───────────────────────────────────────────────────────
OTP_EXPIRY_SECONDS = config("OTP_EXPIRY_SECONDS", 300, cast=int)
OTP_SIMULATE       = config("OTP_SIMULATE", True, cast=bool)
OTP_MAX_ATTEMPTS   = 3

# ── CORS ──────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS   = ["http://localhost:3000", "http://localhost:3001"]

# ── Spectacular ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Yana OS — Auth Service",
    "DESCRIPTION": "Authentication & Authorization for Yana OS platform",
    "VERSION": "1.0.0",
}

# ── Internationalisation ──────────────────────────────────────
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
