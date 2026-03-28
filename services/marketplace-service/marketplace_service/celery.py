import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace_service.settings")
app = Celery("marketplace_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["marketplace_service.core"])
