"""
auth_service/core/admin.py — Django Admin for Auth Service
Supports bulk CSV import/export via django-import-export
"""
import csv
from django.contrib import admin
from django.http import HttpResponse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import AdminUser


class AdminUserResource(resources.ModelResource):
    class Meta:
        model = AdminUser
        import_id_fields = ['email']
        fields = ('full_name', 'email', 'role', 'phone', 'city_id', 'is_active')
        skip_unchanged = True


@admin.register(AdminUser)
class AdminUserAdmin(ImportExportModelAdmin):
    resource_class = AdminUserResource
    list_display   = ('full_name', 'email', 'role', 'phone', 'city_id', 'is_active', 'created_at')
    list_filter    = ('role', 'is_active')
    search_fields  = ('full_name', 'email', 'phone')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login_at')
    ordering       = ('-created_at',)
    actions        = ['deactivate_users', 'activate_users', 'export_csv']

    fieldsets = (
        ('Identity', {'fields': ('full_name', 'email', 'phone')}),
        ('Role & Access', {'fields': ('role', 'city_id', 'hub_id', 'is_active')}),
        ('Metadata', {'fields': ('id', 'created_at', 'updated_at', 'last_login_at'), 'classes': ('collapse',)}),
    )

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')
    activate_users.short_description = 'Activate selected users'

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admin_users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Role', 'Phone', 'City ID', 'Active', 'Created'])
        for u in queryset:
            writer.writerow([
                u.full_name, u.email, u.role, u.phone or '',
                str(u.city_id) if u.city_id else '', u.is_active,
                u.created_at.strftime('%Y-%m-%d')
            ])
        return response
    export_csv.short_description = 'Export selected → CSV'


admin.site.site_header = 'Yana OS — Auth & User Management'
admin.site.site_title  = 'Yana Auth Admin'
admin.site.index_title = 'Auth Service Administration'
