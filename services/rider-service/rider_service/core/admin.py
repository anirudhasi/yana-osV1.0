"""
rider_service/core/admin.py — Django Admin for Rider Service
Supports bulk CSV import/export via django-import-export
"""
import csv
from django.contrib import admin
from django.http import HttpResponse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Rider, RiderDocument, RiderNominee, KYCVerificationLog, RiderStatusAudit


# ── Resources (define importable fields) ────────────────────

class RiderResource(resources.ModelResource):
    class Meta:
        model = Rider
        import_id_fields = ['phone']
        fields = (
            'full_name', 'phone', 'email', 'date_of_birth', 'gender',
            'address_line1', 'address_line2', 'city', 'state', 'pincode',
            'preferred_language', 'status', 'kyc_status', 'source',
        )
        skip_unchanged = True
        report_skipped = True


class RiderDocumentResource(resources.ModelResource):
    class Meta:
        model = RiderDocument
        import_id_fields = ['id']
        fields = ('rider', 'document_type', 'file_url', 'status')
        skip_unchanged = True


# ── Admin classes ────────────────────────────────────────────

@admin.register(Rider)
class RiderAdmin(ImportExportModelAdmin):
    resource_class = RiderResource
    list_display   = ('full_name', 'phone', 'city', 'status', 'kyc_status',
                      'aadhaar_verified', 'pan_verified', 'dl_verified', 'created_at')
    list_filter    = ('status', 'kyc_status', 'city', 'state', 'gender',
                      'aadhaar_verified', 'pan_verified', 'dl_verified', 'bank_verified')
    search_fields  = ('full_name', 'phone', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering       = ('-created_at',)
    date_hierarchy = 'created_at'
    actions        = ['export_csv', 'mark_kyc_pending', 'activate_riders', 'suspend_riders']

    fieldsets = (
        ('Basic Info', {
            'fields': ('full_name', 'phone', 'email', 'date_of_birth', 'gender',
                       'preferred_language', 'profile_photo_url')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'pincode',
                       'latitude', 'longitude')
        }),
        ('Status & Hub', {
            'fields': ('status', 'kyc_status', 'hub_id', 'city_id')
        }),
        ('KYC Verification', {
            'fields': ('aadhaar_verified', 'pan_verified', 'dl_verified', 'bank_verified')
        }),
        ('Training', {
            'fields': ('training_completed', 'training_completed_at', 'activated_at', 'activated_by_id')
        }),
        ('Referral & Source', {
            'fields': ('source', 'referral_code', 'referred_by_id')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'reliability_score'),
            'classes': ('collapse',)
        }),
    )

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="riders_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Phone', 'Email', 'City', 'Status', 'KYC Status',
                         'Aadhaar OK', 'PAN OK', 'DL OK', 'Bank OK', 'Created'])
        for r in queryset:
            writer.writerow([
                r.full_name, r.phone, r.email or '', r.city or '',
                r.status, r.kyc_status,
                r.aadhaar_verified, r.pan_verified, r.dl_verified, r.bank_verified,
                r.created_at.strftime('%Y-%m-%d')
            ])
        return response
    export_csv.short_description = 'Export selected → CSV'

    def mark_kyc_pending(self, request, queryset):
        updated = queryset.filter(status='DOCS_SUBMITTED').update(
            status='KYC_PENDING', kyc_status='SUBMITTED'
        )
        self.message_user(request, f'{updated} rider(s) moved to KYC Pending.')
    mark_kyc_pending.short_description = 'Mark as KYC Pending'

    def activate_riders(self, request, queryset):
        updated = queryset.filter(status='VERIFIED').update(status='ACTIVE')
        self.message_user(request, f'{updated} rider(s) activated.')
    activate_riders.short_description = 'Activate (VERIFIED → ACTIVE)'

    def suspend_riders(self, request, queryset):
        updated = queryset.exclude(status__in=['OFFBOARDED']).update(status='SUSPENDED')
        self.message_user(request, f'{updated} rider(s) suspended.')
    suspend_riders.short_description = 'Suspend selected riders'


@admin.register(RiderDocument)
class RiderDocumentAdmin(ImportExportModelAdmin):
    resource_class = RiderDocumentResource
    list_display   = ('rider', 'document_type', 'status', 'verified_at', 'created_at')
    list_filter    = ('document_type', 'status')
    search_fields  = ('rider__full_name', 'rider__phone')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering       = ('-created_at',)
    actions        = ['approve_documents', 'reject_documents']

    def approve_documents(self, request, queryset):
        updated = queryset.update(status='VERIFIED')
        self.message_user(request, f'{updated} document(s) approved.')
    approve_documents.short_description = 'Approve selected documents'

    def reject_documents(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'{updated} document(s) rejected.')
    reject_documents.short_description = 'Reject selected documents'


@admin.register(RiderNominee)
class RiderNomineeAdmin(admin.ModelAdmin):
    list_display  = ('rider', 'full_name', 'relationship', 'phone', 'is_primary', 'created_at')
    list_filter   = ('relationship', 'is_primary')
    search_fields = ('rider__full_name', 'rider__phone', 'full_name', 'phone')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(KYCVerificationLog)
class KYCVerificationLogAdmin(admin.ModelAdmin):
    list_display  = ('rider', 'action', 'old_status', 'new_status', 'provider', 'created_at')
    list_filter   = ('action', 'new_status', 'provider')
    search_fields = ('rider__full_name', 'rider__phone')
    readonly_fields = ('id', 'created_at')
    ordering      = ('-created_at',)


@admin.register(RiderStatusAudit)
class RiderStatusAuditAdmin(admin.ModelAdmin):
    list_display  = ('rider', 'old_status', 'new_status', 'created_at')
    list_filter   = ('old_status', 'new_status')
    search_fields = ('rider__full_name', 'rider__phone')
    readonly_fields = ('id', 'created_at')
    ordering      = ('-created_at',)


# Admin site branding
admin.site.site_header = 'Yana OS — Rider Management'
admin.site.site_title  = 'Yana Rider Admin'
admin.site.index_title = 'Rider Service Administration'
