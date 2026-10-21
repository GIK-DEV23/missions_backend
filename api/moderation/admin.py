from django.contrib import admin

from moderation.models import ContentReport, UserDeletion


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "content_id", "reason", "status", "created_at")
    list_filter = ("status", "content_type", "reason")
    search_fields = ("details", "resolution_notes")


@admin.register(UserDeletion)
class UserDeletionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "requested_at", "grace_period_ends_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("user__email",)
