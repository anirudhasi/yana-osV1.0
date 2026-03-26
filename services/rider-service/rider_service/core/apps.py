from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "rider_service.core"
    label = "rider_core"
    verbose_name = "Rider Core"
