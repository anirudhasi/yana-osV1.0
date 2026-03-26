import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fleet_service.settings")
app = Celery("fleet_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["fleet_service.core"])
