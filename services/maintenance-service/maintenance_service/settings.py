"""Yana OS — Maintenance Service Settings"""
import os, re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY    = config("SECRET_KEY", "maintenance-dev-secret")
DEBUG         = config("DEBUG", False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "*").split(",")
SERVICE_NAME  = "maintenance-service"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "import_export",
    "maintenance_service.core",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF     = "maintenance_service.urls"
WSGI_APPLICATION = "maintenance_service.wsgi.application"

_db = config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os")
_m  = re.match(r"postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _db)
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
    "NAME": _m.group(5) if _m else "yana_os", "USER": _m.group(1) if _m else "yana_user",
    "PASSWORD": _m.group(2) if _m else "yana_secret", "HOST": _m.group(3) if _m else "postgres",
    "PORT": _m.group(4) if _m else "5432", "OPTIONS": {"options": "-c search_path=public"}}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = config("REDIS_URL", "redis://redis:6379/9")
CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": REDIS_URL,
    "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}, "TIMEOUT": 600}}

CELERY_BROKER_URL     = config("CELERY_BROKER_URL", "redis://redis:6379/10")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/10")
CELERY_TASK_SERIALIZER = CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_BEAT_SCHEDULE = {
    "check-service-alerts": {"task": "maintenance_service.core.tasks.check_service_alerts", "schedule": 3600},
    "check-compliance-expiry": {"task": "maintenance_service.core.tasks.check_compliance_expiry", "schedule": 86400},
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["maintenance_service.core.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "maintenance_service.core.authentication.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "maintenance_service.core.authentication.StandardPagination",
    "PAGE_SIZE": 20,
}
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)
CORS_ALLOW_ALL_ORIGINS = DEBUG
LANGUAGE_CODE = "en-us"; TIME_ZONE = "Asia/Kolkata"; USE_I18N = True; USE_TZ = True
# Shared DB: skip admin/sessions migrations — tables created by rider-service
MIGRATION_MODULES = {"admin": None, "sessions": None}
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [],
              "APP_DIRS": True, "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages",
              ]}}]
SPECTACULAR_SETTINGS = {"TITLE": "Yana OS — Maintenance Service", "VERSION": "1.0.0"}
