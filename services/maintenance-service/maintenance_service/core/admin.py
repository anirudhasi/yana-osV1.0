"""
maintenance_service/core/admin.py

Django admin with django-import-export for:
  MaintenanceLog, MaintenanceAlert
  (Vehicle and AdminUser are unmanaged stubs — not registered)
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import MaintenanceLog, MaintenanceAlert

# ── Admin branding ─────────────────────────────────────────────
admin.site.site_header = "Yana OS — Maintenance"
admin.site.site_title  = "Yana OS — Maintenance"
admin.site.index_title = "Maintenance Administration"


# ── Import-Export Resources ────────────────────────────────────

class MaintenanceLogResource(resources.ModelResource):
    """
    Bulk import resource for MaintenanceLog.
    Fields: vehicle_id, maintenance_type, description, labour_cost,
            parts_cost, status
    (spec mentions 'work_type' and 'cost' — mapped to model's
     maintenance_type, labour_cost + parts_cost)
    """
    class Meta:
        model          = MaintenanceLog
        fields         = (
            "id", "vehicle_id", "hub_id", "maintenance_type",
            "description", "labour_cost", "parts_cost", "status",
        )
        skip_unchanged = True
        report_skipped = True


# ── CSV export helper ──────────────────────────────────────────

def export_csv(modeladmin, request, queryset):
    """Generic CSV export action."""
    meta        = modeladmin.model._meta
    field_names = [f.name for f in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{meta.model_name}_{timezone.now().date()}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response

export_csv.short_description = "Export selected rows as CSV"


# ── Custom actions ─────────────────────────────────────────────

def complete_work_orders(modeladmin, request, queryset):
    now     = timezone.now()
    updated = queryset.filter(status="IN_PROGRESS").update(
        status="COMPLETED", completed_at=now
    )
    modeladmin.message_user(request, f"{updated} work order(s) marked as COMPLETED.")

complete_work_orders.short_description = "Mark selected work orders as Completed"


def acknowledge_alerts(modeladmin, request, queryset):
    now     = timezone.now()
    updated = queryset.filter(is_acknowledged=False).update(
        is_acknowledged=True, acknowledged_at=now
    )
    modeladmin.message_user(request, f"{updated} alert(s) acknowledged.")

acknowledge_alerts.short_description = "Acknowledge selected alerts"


# ── Helper: display total cost on list view ────────────────────

def total_cost_display(obj):
    return f"₹{float(obj.labour_cost) + float(obj.parts_cost):.2f}"

total_cost_display.short_description = "Total Cost"


# ── ModelAdmin registrations ───────────────────────────────────

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(ImportExportModelAdmin):
    resource_class  = MaintenanceLogResource
    list_display    = (
        "vehicle_id", "maintenance_type", "status", "logged_by_id",
        total_cost_display, "started_at", "completed_at",
    )
    list_filter     = ("status", "maintenance_type")
    search_fields   = ("vehicle_id",)
    actions         = [complete_work_orders, export_csv]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(MaintenanceAlert)
class MaintenanceAlertAdmin(admin.ModelAdmin):
    list_display    = (
        "vehicle_id", "alert_type", "severity", "is_acknowledged", "created_at",
    )
    list_filter     = ("severity", "alert_type", "is_acknowledged")
    search_fields   = ("vehicle_id",)
    actions         = [acknowledge_alerts]
    readonly_fields = ("id", "created_at")
