from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'type', 'is_read', 'created_at')
    search_fields = ('title', 'body', 'user__first_name', 'user__last_name')
    list_filter = ('type', 'is_read')
    ordering = ('-created_at',)
