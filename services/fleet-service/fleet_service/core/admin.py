"""
fleet_service/core/admin.py — Django Admin for Fleet Service
Supports bulk CSV import/export via django-import-export
"""
import csv
from django.contrib import admin
from django.http import HttpResponse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    City, FleetHub, Vehicle, VehicleAllotment,
    MaintenanceAlert, VehicleStatusAudit,
)


# ── Resources ────────────────────────────────────────────────

class CityResource(resources.ModelResource):
    class Meta:
        model = City
        import_id_fields = ['name']
        fields = ('name', 'state', 'is_active')
        skip_unchanged = True
        report_skipped = True


class FleetHubResource(resources.ModelResource):
    class Meta:
        model = FleetHub
        import_id_fields = ['name']
        fields = ('name', 'city', 'address', 'capacity', 'is_active')
        skip_unchanged = True
        report_skipped = True


class VehicleResource(resources.ModelResource):
    class Meta:
        model = Vehicle
        import_id_fields = ['registration_number']
        fields = (
            'registration_number', 'make', 'model', 'manufacturing_year',
            'status', 'hub', 'color', 'chassis_number',
            'insurance_expiry', 'puc_expiry', 'fitness_expiry',
        )
        skip_unchanged = True
        report_skipped = True


# ── City ─────────────────────────────────────────────────────

@admin.register(City)
class CityAdmin(ImportExportModelAdmin):
    resource_class = CityResource
    list_display   = ('name', 'state', 'is_active', 'created_at')
    list_filter    = ('state', 'is_active')
    search_fields  = ('name', 'state')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering       = ('name',)
    actions        = ['activate_cities', 'deactivate_cities', 'export_csv']

    def activate_cities(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} city/cities activated.')
    activate_cities.short_description = 'Activate selected cities'

    def deactivate_cities(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} city/cities deactivated.')
    deactivate_cities.short_description = 'Deactivate selected cities'

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cities_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'State', 'Active', 'Created'])
        for c in queryset:
            writer.writerow([c.name, c.state, c.is_active, c.created_at.strftime('%Y-%m-%d')])
        return response
    export_csv.short_description = 'Export selected → CSV'


# ── FleetHub ─────────────────────────────────────────────────

@admin.register(FleetHub)
class FleetHubAdmin(ImportExportModelAdmin):
    resource_class = FleetHubResource
    list_display   = ('name', 'city', 'capacity', 'available_count',
                      'allocated_count', 'utilization_pct', 'is_active', 'created_at')
    list_filter    = ('city', 'is_active')
    search_fields  = ('name', 'city__name', 'address')
    readonly_fields = ('id', 'created_at', 'updated_at', 'available_count',
                       'allocated_count', 'utilization_pct')
    ordering       = ('city__name', 'name')
    actions        = ['activate_hubs', 'deactivate_hubs', 'export_csv']

    fieldsets = (
        ('Hub Info', {'fields': ('name', 'city', 'address', 'capacity', 'is_active')}),
        ('Location', {'fields': ('latitude', 'longitude')}),
        ('Management', {'fields': ('manager_id',)}),
        ('Stats', {'fields': ('available_count', 'allocated_count', 'utilization_pct')}),
        ('Metadata', {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def activate_hubs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} hub(s) activated.')
    activate_hubs.short_description = 'Activate selected hubs'

    def deactivate_hubs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} hub(s) deactivated.')
    deactivate_hubs.short_description = 'Deactivate selected hubs'

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fleet_hubs_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'City', 'Address', 'Capacity', 'Active', 'Created'])
        for h in queryset:
            writer.writerow([
                h.name, h.city.name, h.address, h.capacity, h.is_active,
                h.created_at.strftime('%Y-%m-%d')
            ])
        return response
    export_csv.short_description = 'Export selected → CSV'


# ── Vehicle ───────────────────────────────────────────────────

@admin.register(Vehicle)
class VehicleAdmin(ImportExportModelAdmin):
    resource_class = VehicleResource
    list_display   = ('registration_number', 'make', 'model', 'manufacturing_year',
                      'hub', 'status', 'battery_level_pct', 'current_odometer_km',
                      'insurance_expiry', 'puc_expiry', 'created_at')
    list_filter    = ('status', 'hub', 'hub__city', 'make', 'is_charging')
    search_fields  = ('registration_number', 'chassis_number', 'motor_number',
                      'make', 'model')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_gps_at',
                       'needs_service', 'compliance_warnings')
    ordering       = ('-created_at',)
    date_hierarchy = 'created_at'
    actions        = ['mark_available', 'mark_maintenance', 'mark_retired', 'export_csv']

    fieldsets = (
        ('Identity', {
            'fields': ('registration_number', 'chassis_number', 'motor_number',
                       'make', 'model', 'manufacturing_year', 'color', 'hub')
        }),
        ('EV Specs', {
            'fields': ('battery_capacity_kwh', 'battery_health_pct', 'range_km', 'max_speed_kmh')
        }),
        ('Live Telemetry', {
            'fields': ('status', 'current_odometer_km', 'battery_level_pct', 'is_charging',
                       'last_gps_lat', 'last_gps_lng', 'last_gps_at')
        }),
        ('Compliance', {
            'fields': ('insurance_expiry', 'puc_expiry', 'fitness_expiry',
                       'rc_document_url', 'insurance_document_url',
                       'compliance_warnings')
        }),
        ('Servicing', {
            'fields': ('next_service_km', 'next_service_date', 'needs_service')
        }),
        ('Financial', {
            'fields': ('purchase_price', 'purchase_date')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    def mark_available(self, request, queryset):
        updated = queryset.filter(status='MAINTENANCE').update(status='AVAILABLE')
        self.message_user(request, f'{updated} vehicle(s) marked as Available.')
    mark_available.short_description = 'Mark as Available'

    def mark_maintenance(self, request, queryset):
        updated = queryset.filter(status='AVAILABLE').update(status='MAINTENANCE')
        self.message_user(request, f'{updated} vehicle(s) sent to Maintenance.')
    mark_maintenance.short_description = 'Send to Maintenance'

    def mark_retired(self, request, queryset):
        updated = queryset.exclude(status='ALLOCATED').update(status='RETIRED')
        self.message_user(request, f'{updated} vehicle(s) retired.')
    mark_retired.short_description = 'Retire selected vehicles'

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vehicles_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Reg No', 'Make', 'Model', 'Year', 'Hub', 'Status',
            'Battery %', 'Odometer (km)', 'Insurance Expiry', 'PUC Expiry', 'Created'
        ])
        for v in queryset:
            writer.writerow([
                v.registration_number, v.make or '', v.model or '',
                v.manufacturing_year or '', str(v.hub), v.status,
                v.battery_level_pct or '', v.current_odometer_km,
                v.insurance_expiry or '', v.puc_expiry or '',
                v.created_at.strftime('%Y-%m-%d')
            ])
        return response
    export_csv.short_description = 'Export selected → CSV'


# ── VehicleAllotment ─────────────────────────────────────────

@admin.register(VehicleAllotment)
class VehicleAllotmentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'rider_id', 'vehicle', 'hub', 'status',
                     'allotted_at', 'expected_return_at', 'returned_at')
    list_filter   = ('status', 'hub')
    search_fields = ('rider_id__icontains', 'vehicle__registration_number')
    readonly_fields = ('id', 'allotted_at', 'created_at', 'updated_at', 'km_driven')
    ordering      = ('-allotted_at',)

    fieldsets = (
        ('Allotment', {
            'fields': ('rider_id', 'vehicle', 'hub', 'status', 'allotted_by_id')
        }),
        ('Timing', {
            'fields': ('allotted_at', 'expected_return_at', 'returned_at', 'returned_to_hub_id')
        }),
        ('Condition', {
            'fields': ('odometer_at_allotment', 'odometer_at_return', 'km_driven',
                       'battery_pct_at_allotment', 'battery_pct_at_return',
                       'condition_at_allotment', 'condition_at_return', 'damage_notes')
        }),
        ('Pricing', {
            'fields': ('daily_rent_amount', 'security_deposit',
                       'deposit_refunded', 'deposit_refund_amount')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ── MaintenanceAlert ─────────────────────────────────────────

@admin.register(MaintenanceAlert)
class MaintenanceAlertAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'alert_type', 'severity', 'is_acknowledged',
                     'acknowledged_at', 'resolved_at', 'created_at')
    list_filter   = ('severity', 'is_acknowledged', 'alert_type')
    search_fields = ('vehicle__registration_number', 'alert_type', 'message')
    readonly_fields = ('id', 'created_at')
    ordering      = ('-created_at',)
    actions       = ['acknowledge_alerts', 'resolve_alerts']

    def acknowledge_alerts(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_acknowledged=False).update(
            is_acknowledged=True,
            acknowledged_at=timezone.now(),
            acknowledged_by_id=None,
        )
        self.message_user(request, f'{updated} alert(s) acknowledged.')
    acknowledge_alerts.short_description = 'Acknowledge selected alerts'

    def resolve_alerts(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(resolved_at__isnull=True).update(
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} alert(s) resolved.')
    resolve_alerts.short_description = 'Mark alerts as resolved'


# ── VehicleStatusAudit ───────────────────────────────────────

@admin.register(VehicleStatusAudit)
class VehicleStatusAuditAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'old_status', 'new_status', 'changed_by_id', 'created_at')
    list_filter   = ('old_status', 'new_status')
    search_fields = ('vehicle__registration_number',)
    readonly_fields = ('id', 'created_at')
    ordering      = ('-created_at',)


# Admin site branding
admin.site.site_header = 'Yana OS — Fleet Management'
admin.site.site_title  = 'Yana Fleet Admin'
admin.site.index_title = 'Fleet Service Administration'
