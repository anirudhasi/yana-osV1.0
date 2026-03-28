from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "marketplace_service.core"
    label = "marketplace_core"
    verbose_name = "Marketplace Core"
