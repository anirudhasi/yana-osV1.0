from django.apps import AppConfig
class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "maintenance_service.core"
    label = "maintenance_core"
    verbose_name = "Maintenance Core"
