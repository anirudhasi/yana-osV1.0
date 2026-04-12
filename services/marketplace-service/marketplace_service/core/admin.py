"""
marketplace_service/core/admin.py

Django admin with django-import-export for:
  Client, ClientDarkStore, ClientContract, DemandSlot, DemandApplication
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    Client,
    ClientDarkStore,
    ClientContract,
    DemandSlot,
    DemandApplication,
)

# ── Admin branding ─────────────────────────────────────────────
admin.site.site_header = "Yana OS — Marketplace & Demand"
admin.site.site_title  = "Yana OS — Marketplace & Demand"
admin.site.index_title = "Marketplace & Demand Administration"


# ── Import-Export Resources ────────────────────────────────────

class ClientResource(resources.ModelResource):
    """
    Bulk import resource for Client.
    Model fields used: name, category, primary_contact_email,
                       primary_contact_phone, is_active
    (The spec mentions 'code' and 'industry' — mapped to available fields)
    """
    class Meta:
        model          = Client
        fields         = (
            "id", "name", "category", "primary_contact_email",
            "primary_contact_phone", "is_active",
        )
        skip_unchanged = True
        report_skipped = True


class DemandSlotResource(resources.ModelResource):
    """
    Bulk import resource for DemandSlot.
    Model fields: client_id, dark_store_id, shift_date, shift_start_time,
                  shift_end_time, riders_required, pay_per_shift, status
    (spec mentions start_time/end_time/payout_amount — mapped to model names)
    """
    class Meta:
        model          = DemandSlot
        fields         = (
            "client_id", "dark_store_id", "city_id",
            "title", "shift_date", "shift_start_time", "shift_end_time",
            "riders_required", "pay_per_shift", "status",
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

def activate_clients(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} client(s) activated.")

activate_clients.short_description = "Activate selected clients"


def deactivate_clients(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} client(s) deactivated.")

deactivate_clients.short_description = "Deactivate selected clients"


def publish_slots(modeladmin, request, queryset):
    updated = queryset.filter(status="DRAFT").update(
        status="PUBLISHED", published_at=timezone.now()
    )
    modeladmin.message_user(request, f"{updated} demand slot(s) published.")

publish_slots.short_description = "Publish selected demand slots"


def cancel_slots(modeladmin, request, queryset):
    updated = queryset.exclude(status__in=["FILLED", "CANCELLED"]).update(
        status="CANCELLED"
    )
    modeladmin.message_user(request, f"{updated} demand slot(s) cancelled.")

cancel_slots.short_description = "Cancel selected demand slots"


def confirm_applications(modeladmin, request, queryset):
    updated = queryset.filter(status__in=["APPLIED", "SHORTLISTED"]).update(
        status="CONFIRMED", confirmed_at=timezone.now()
    )
    modeladmin.message_user(request, f"{updated} application(s) confirmed.")

confirm_applications.short_description = "Confirm selected applications"


def shortlist_applications(modeladmin, request, queryset):
    updated = queryset.filter(status="APPLIED").update(status="SHORTLISTED")
    modeladmin.message_user(request, f"{updated} application(s) shortlisted.")

shortlist_applications.short_description = "Shortlist selected applications"


# ── ModelAdmin registrations ───────────────────────────────────

@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    resource_class  = ClientResource
    list_display    = (
        "name", "category", "primary_contact_email",
        "primary_contact_phone", "is_active", "created_at",
    )
    list_filter     = ("category", "is_active")
    search_fields   = ("name", "primary_contact_email")
    actions         = [activate_clients, deactivate_clients, export_csv]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ClientDarkStore)
class ClientDarkStoreAdmin(ImportExportModelAdmin):
    list_display    = ("name", "client", "city_id", "hub_id", "is_active")
    list_filter     = ("is_active",)
    search_fields   = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ClientContract)
class ClientContractAdmin(admin.ModelAdmin):
    list_display    = (
        "client", "dark_store", "contract_start", "contract_end",
        "pay_per_shift", "is_active",
    )
    list_filter     = ("is_active",)
    search_fields   = ("client__name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DemandSlot)
class DemandSlotAdmin(ImportExportModelAdmin):
    resource_class  = DemandSlotResource
    list_display    = (
        "client", "dark_store", "shift_start_time", "shift_end_time",
        "riders_required", "riders_confirmed", "status", "pay_per_shift",
    )
    list_filter     = ("status",)
    search_fields   = ("client__name", "title")
    actions         = [publish_slots, cancel_slots, export_csv]
    readonly_fields = ("id", "created_at", "updated_at", "fill_rate_pct")


@admin.register(DemandApplication)
class DemandApplicationAdmin(admin.ModelAdmin):
    list_display    = ("demand_slot", "rider_id", "status", "applied_at")
    list_filter     = ("status",)
    search_fields   = ("rider_id",)
    actions         = [confirm_applications, shortlist_applications]
    readonly_fields = ("id", "created_at", "updated_at", "applied_at")
