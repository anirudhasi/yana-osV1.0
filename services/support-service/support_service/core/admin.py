"""
support_service/core/admin.py

Django admin with django-import-export for:
  SupportTicket, TicketMessage
  (Rider and AdminUser are unmanaged stubs — not registered)
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import SupportTicket, TicketMessage

# ── Admin branding ─────────────────────────────────────────────
admin.site.site_header = "Yana OS — Support & Tickets"
admin.site.site_title  = "Yana OS — Support & Tickets"
admin.site.index_title = "Support & Tickets Administration"


# ── Import-Export Resources ────────────────────────────────────

class SupportTicketResource(resources.ModelResource):
    """
    Bulk import resource for SupportTicket.
    Fields: rider_id, category, subject, description, priority
    ticket_number is auto-generated via save() signal — omit from import.
    """
    class Meta:
        model          = SupportTicket
        fields         = (
            "id", "rider_id", "category", "subject", "description", "priority",
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

def assign_to_me(modeladmin, request, queryset):
    """
    Bulk 'assign to me' is not supported via list action because we cannot
    reliably map the Django auth user to an AdminUser UUID here.
    Direct the operator to use the ticket detail view for assignment.
    """
    modeladmin.message_user(
        request,
        "To assign tickets, please open each ticket's detail page and "
        "set the 'assigned_to_id' field manually."
    )

assign_to_me.short_description = "Assign to me (see detail view)"


def resolve_tickets(modeladmin, request, queryset):
    now     = timezone.now()
    updated = queryset.exclude(
        status__in=["RESOLVED", "CLOSED"]
    ).update(status="RESOLVED", resolved_at=now)
    modeladmin.message_user(request, f"{updated} ticket(s) marked as RESOLVED.")

resolve_tickets.short_description = "Mark selected tickets as Resolved"


def close_tickets(modeladmin, request, queryset):
    updated = queryset.exclude(status="CLOSED").update(status="CLOSED")
    modeladmin.message_user(request, f"{updated} ticket(s) closed.")

close_tickets.short_description = "Close selected tickets"


# ── ModelAdmin registrations ───────────────────────────────────

@admin.register(SupportTicket)
class SupportTicketAdmin(ImportExportModelAdmin):
    resource_class  = SupportTicketResource
    list_display    = (
        "ticket_number", "rider_id", "category", "subject",
        "status", "priority", "assigned_to_id", "created_at",
    )
    list_filter     = ("status", "priority", "category")
    search_fields   = ("ticket_number", "rider_id", "subject")
    ordering        = ("-created_at",)
    actions         = [assign_to_me, resolve_tickets, close_tickets, export_csv]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display    = (
        "ticket", "sender_type", "sender_rider_id", "sender_admin_id", "created_at",
    )
    list_filter     = ("sender_type",)
    search_fields   = ("ticket__ticket_number",)
    readonly_fields = ("id", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
