from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "auth_service.core"
    label = "auth_core"
    verbose_name = "Auth Core"
