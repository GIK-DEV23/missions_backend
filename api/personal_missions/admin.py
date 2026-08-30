from django.contrib import admin

from personal_missions.models import PersonalMission


@admin.register(PersonalMission)
class PersonalMissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'name', 'type', 'rhythm', 'archived_at', 'created_at')
    search_fields = ('name', 'owner__first_name', 'owner__last_name')
    list_filter = ('type', 'rhythm', 'reminder_enabled')
    ordering = ('-created_at',)
