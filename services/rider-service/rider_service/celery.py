import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rider_service.settings")

app = Celery("rider_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["rider_service.core"])
