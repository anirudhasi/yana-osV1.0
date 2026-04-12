"""
skills_service/core/admin.py

Django admin with django-import-export for:
  SkillModule, SkillVideo, RiderSkillProgress, RiderGamification, RiderBadge
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    SkillModule,
    SkillVideo,
    RiderSkillProgress,
    RiderGamification,
    RiderBadge,
)

# ── Admin branding ─────────────────────────────────────────────
admin.site.site_header = "Yana OS — Skills & Training"
admin.site.site_title  = "Yana OS — Skills & Training"
admin.site.index_title = "Skills & Training Administration"


# ── Import-Export Resources ────────────────────────────────────

class SkillModuleResource(resources.ModelResource):
    """
    Bulk import resource for SkillModule.
    Fields: title, description, thumbnail_url, sequence_order,
            is_mandatory, is_published
    (spec mentions 'category' and 'level' — SkillModule has no such fields;
     sequence_order is used for ordering instead)
    """
    class Meta:
        model          = SkillModule
        fields         = (
            "id", "title", "description", "thumbnail_url",
            "sequence_order", "is_mandatory", "is_published",
        )
        skip_unchanged = True
        report_skipped = True


class SkillVideoResource(resources.ModelResource):
    """
    Bulk import resource for SkillVideo.
    Fields: module_id, title, video_url, duration_secs,
            sequence_order, is_published
    (spec mentions 'duration_seconds' — model uses 'duration_secs')
    """
    class Meta:
        model          = SkillVideo
        fields         = (
            "id", "module_id", "title", "video_url",
            "duration_secs", "sequence_order", "is_published",
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

def publish_modules(modeladmin, request, queryset):
    updated = queryset.update(is_published=True)
    modeladmin.message_user(request, f"{updated} module(s) published.")

publish_modules.short_description = "Publish selected modules"


def unpublish_modules(modeladmin, request, queryset):
    updated = queryset.update(is_published=False)
    modeladmin.message_user(request, f"{updated} module(s) unpublished.")

unpublish_modules.short_description = "Unpublish selected modules"


# ── ModelAdmin registrations ───────────────────────────────────

@admin.register(SkillModule)
class SkillModuleAdmin(ImportExportModelAdmin):
    resource_class  = SkillModuleResource
    list_display    = (
        "title", "sequence_order", "is_mandatory",
        "is_published", "created_at",
    )
    list_filter     = ("is_mandatory", "is_published")
    search_fields   = ("title",)
    actions         = [publish_modules, unpublish_modules, export_csv]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SkillVideo)
class SkillVideoAdmin(ImportExportModelAdmin):
    resource_class  = SkillVideoResource
    list_display    = (
        "module", "title", "sequence_order", "duration_secs", "is_published",
    )
    list_filter     = ("is_published", "module")
    search_fields   = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RiderSkillProgress)
class RiderSkillProgressAdmin(admin.ModelAdmin):
    list_display    = (
        "rider_id", "module", "video", "watch_time_secs",
        "is_completed", "completed_at",
    )
    list_filter     = ("is_completed",)
    search_fields   = ("rider_id",)
    readonly_fields = ("id", "started_at")


@admin.register(RiderGamification)
class RiderGamificationAdmin(admin.ModelAdmin):
    list_display    = (
        "rider_id", "total_points", "streak_days",
        "current_level", "updated_at",
    )
    search_fields   = ("rider_id",)
    readonly_fields = ("id", "updated_at")


@admin.register(RiderBadge)
class RiderBadgeAdmin(admin.ModelAdmin):
    list_display    = ("rider_id", "badge_code", "badge_name", "earned_at")
    list_filter     = ("badge_code",)
    search_fields   = ("rider_id",)
    readonly_fields = ("id", "earned_at")
