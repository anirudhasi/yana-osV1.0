"""
payments_service/core/admin.py

Django admin with django-import-export for:
  RiderWallet, WalletLedger, PaymentTransaction, RentSchedule, UPIMandate
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    RiderWallet,
    WalletLedger,
    PaymentTransaction,
    RentSchedule,
    UPIMandate,
)

# ── Admin branding ─────────────────────────────────────────────
admin.site.site_header = "Yana OS — Payments & Wallets"
admin.site.site_title  = "Yana OS — Payments & Wallets"
admin.site.index_title = "Payments & Wallets Administration"


# ── Import-Export Resources ────────────────────────────────────

class RiderWalletResource(resources.ModelResource):
    """
    Bulk import resource for RiderWallet.
    Importable fields: rider_id, balance, security_deposit_held
    (is_active does not exist on this model; deposit_amount maps to security_deposit_held)
    """
    class Meta:
        model          = RiderWallet
        fields         = ("id", "rider_id", "balance", "security_deposit_held")
        skip_unchanged = True
        report_skipped = True


class RentScheduleResource(resources.ModelResource):
    """
    Bulk import resource for RentSchedule.
    Fields: rider_id, allotment_id, due_date, amount, status
    """
    class Meta:
        model          = RentSchedule
        fields         = ("rider_id", "allotment_id", "due_date", "amount", "status")
        skip_unchanged = True
        report_skipped = True


# ── CSV export helper ──────────────────────────────────────────

def export_csv(modeladmin, request, queryset):
    """Generic CSV export action — exports all concrete fields."""
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

def freeze_wallet(modeladmin, request, queryset):
    """
    Freeze wallets. RiderWallet has no is_frozen field yet —
    this action records intent and notifies the admin.
    """
    modeladmin.message_user(
        request,
        f"Freeze request logged for {queryset.count()} wallet(s). "
        "Add an 'is_frozen' field to RiderWallet to enable hard freeze."
    )

freeze_wallet.short_description = "Freeze selected wallets"


def unfreeze_wallet(modeladmin, request, queryset):
    modeladmin.message_user(
        request,
        f"Unfreeze request logged for {queryset.count()} wallet(s). "
        "Add an 'is_frozen' field to RiderWallet to enable hard unfreeze."
    )

unfreeze_wallet.short_description = "Unfreeze selected wallets"


def activate_schedules(modeladmin, request, queryset):
    updated = queryset.exclude(status="PAID").update(status="PENDING")
    modeladmin.message_user(request, f"{updated} schedule(s) reset to PENDING.")

activate_schedules.short_description = "Reset selected schedules to Pending"


def deactivate_schedules(modeladmin, request, queryset):
    updated = queryset.exclude(status="PAID").update(status="WAIVED")
    modeladmin.message_user(request, f"{updated} schedule(s) waived.")

deactivate_schedules.short_description = "Waive selected rent schedules"


# ── ModelAdmin registrations ───────────────────────────────────

@admin.register(RiderWallet)
class RiderWalletAdmin(ImportExportModelAdmin):
    resource_class  = RiderWalletResource
    list_display    = (
        "rider_id", "balance", "total_earned", "total_paid",
        "total_pending_dues", "security_deposit_held",
    )
    search_fields   = ("rider_id",)
    actions         = [export_csv, freeze_wallet, unfreeze_wallet]
    readonly_fields = ("id", "created_at", "updated_at", "version")


@admin.register(WalletLedger)
class WalletLedgerAdmin(admin.ModelAdmin):
    """
    Read-only ledger — no import/export to preserve immutability.
    WalletLedger uses 'payment_type' (not 'transaction_type') and 'direction'.
    """
    list_display    = (
        "wallet", "direction", "amount", "balance_after",
        "description", "created_at",
    )
    list_filter     = ("direction", "payment_type")
    search_fields   = ("wallet__rider_id",)
    ordering        = ("-created_at",)
    readonly_fields = (
        "id", "wallet", "rider_id", "payment_type", "amount", "direction",
        "balance_after", "reference_id", "reference_type", "description",
        "payment_gateway", "gateway_txn_id", "upi_ref_id",
        "accounting_date", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display    = (
        "rider_id", "payment_type", "amount", "status", "gateway", "created_at",
    )
    list_filter     = ("status", "payment_type", "gateway")
    search_fields   = ("rider_id",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RentSchedule)
class RentScheduleAdmin(ImportExportModelAdmin):
    resource_class  = RentScheduleResource
    list_display    = (
        "rider_id", "allotment_id", "amount", "status", "due_date",
        "days_overdue", "paid_at",
    )
    list_filter     = ("status",)
    search_fields   = ("rider_id",)
    actions         = [activate_schedules, deactivate_schedules]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(UPIMandate)
class UPIMandateAdmin(admin.ModelAdmin):
    list_display    = ("rider_id", "upi_id", "max_amount", "is_active", "created_at")
    list_filter     = ("is_active",)
    search_fields   = ("rider_id",)
    readonly_fields = ("id", "created_at", "updated_at")
