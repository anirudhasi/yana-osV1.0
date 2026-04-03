"""Yana OS — Skills Service Settings"""
import os, re
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY    = config("SECRET_KEY", "skills-dev-secret")
DEBUG         = config("DEBUG", False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", "*").split(",")
SERVICE_NAME  = "skills-service"

INSTALLED_APPS = [
    "django.contrib.contenttypes", "django.contrib.auth",
    "rest_framework", "corsheaders", "drf_spectacular",
    "django_celery_beat", "skills_service.core",
]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware",
              "django.middleware.security.SecurityMiddleware",
              "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF     = "skills_service.urls"
WSGI_APPLICATION = "skills_service.wsgi.application"

_db = config("DATABASE_URL", "postgres://yana_user:yana_secret@postgres:5432/yana_os")
_m  = re.match(r"postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _db)
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
    "NAME": _m.group(5) if _m else "yana_os", "USER": _m.group(1) if _m else "yana_user",
    "PASSWORD": _m.group(2) if _m else "yana_secret", "HOST": _m.group(3) if _m else "postgres",
    "PORT": _m.group(4) if _m else "5432", "OPTIONS": {"options": "-c search_path=public"}}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = config("REDIS_URL", "redis://redis:6379/11")
CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": REDIS_URL,
    "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}, "TIMEOUT": 600}}

CELERY_BROKER_URL     = config("CELERY_BROKER_URL", "redis://redis:6379/12")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://redis:6379/12")
CELERY_TASK_SERIALIZER = CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT  = ["json"]
CELERY_TIMEZONE        = "Asia/Kolkata"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["skills_service.core.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "skills_service.core.authentication.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "skills_service.core.authentication.StandardPagination",
    "PAGE_SIZE": 20,
}
JWT_SECRET_KEY = config("JWT_SECRET_KEY", SECRET_KEY)

# MinIO for video storage
MINIO_ENDPOINT   = config("MINIO_ENDPOINT",   "minio:9000")
MINIO_ACCESS_KEY = config("MINIO_ACCESS_KEY", "yana_minio")
MINIO_SECRET_KEY = config("MINIO_SECRET_KEY", "yana_minio_secret")
MINIO_BUCKET     = config("MINIO_BUCKET",     "yana-skills")
MINIO_USE_SSL    = config("MINIO_USE_SSL",    False, cast=bool)

# Gamification config
POINTS_PER_VIDEO_WATCH   = 10
POINTS_PER_QUIZ_PASS     = 25
POINTS_PER_MODULE_COMPLETE = 100
LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2500]  # XP needed per level

CORS_ALLOW_ALL_ORIGINS = DEBUG
LANGUAGE_CODE = "en-us"; TIME_ZONE = "Asia/Kolkata"; USE_I18N = True; USE_TZ = True
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [],
              "APP_DIRS": True, "OPTIONS": {"context_processors": []}}]
SPECTACULAR_SETTINGS = {"TITLE": "Yana OS — Skills Service", "VERSION": "1.0.0"}
