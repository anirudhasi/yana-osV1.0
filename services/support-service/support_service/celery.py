import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "support_service.settings")
app = Celery("support_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["support_service.core"])
