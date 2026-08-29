from typing import Any, Dict, Optional

from django.db import models
from django.http import HttpRequest

from base.models import BaseModel, client_id_field
from personal_missions.constants import PersonalMissionType, PersonalMissionRhythm


class PersonalMission(BaseModel):
    client_id = client_id_field()
    owner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name='personal_missions')
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=PersonalMissionType.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rhythm = models.CharField(max_length=20, choices=PersonalMissionRhythm.choices, default=PersonalMissionRhythm.NONE)
    rhythm_day = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0-6, Monday-Sunday")
    location = models.CharField(max_length=200, null=True, blank=True)
    reminder_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    what_happened = models.TextField(null=True, blank=True, help_text="One-time missions only")

    class Meta:
        db_table = "personal_missions"

    def __str__(self):
        return self.name

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "owner_id": self.owner.id if self.owner else None,
        })
        return data
