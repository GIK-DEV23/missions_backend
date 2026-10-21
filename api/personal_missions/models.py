from typing import Any, Dict, Optional

from django.core.validators import MinValueValidator, MaxValueValidator
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
    rhythm_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0-6, Monday-Sunday",
    )
    location = models.CharField(max_length=200, null=True, blank=True)
    reminder_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    what_happened = models.TextField(null=True, blank=True, help_text="One-time missions only")

    class Meta:
        db_table = "personal_missions"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "client_id"],
                name="uniq_personal_mission_owner_client",
            ),
        ]

    def __str__(self):
        return self.name

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "owner_id": self.owner.id if self.owner else None,
        })
        return data


class PersonalMissionPeriod(BaseModel):
    """
    Tracks when a user met their rhythm commitment for a personal mission.
    
    Only stores MET periods — missing rows indicate missed periods.
    The unique constraint ensures concurrent sync operations are idempotent.
    """
    mission = models.ForeignKey(
        PersonalMission,
        on_delete=models.CASCADE,
        related_name="met_periods",
    )
    period_index = models.IntegerField(
        help_text="0-based index computed from mission start_date and rhythm",
    )
    period_start = models.DateField(help_text="First day of this period")
    period_end = models.DateField(help_text="Last day of this period")
    met_at = models.DateTimeField(help_text="When the period was marked as met")

    class Meta:
        db_table = "personal_mission_periods"
        constraints = [
            models.UniqueConstraint(
                fields=["mission", "period_index"],
                name="unique_mission_period",
            ),
        ]
        indexes = [
            models.Index(fields=["mission", "period_index"]),
        ]

    def __str__(self):
        return f"{self.mission.name} - Period {self.period_index}"

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "mission_id": self.mission_id,
        })
        return data


class PersonalMissionSession(BaseModel):
    """
    Explicit session log for a personal mission.
    
    Allows users to record "I did my mission today" even when no new souls
    were added and no check-ins were logged. Triggers rhythm tracking.
    """
    mission = models.ForeignKey(
        PersonalMission,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    date = models.DateField(help_text="Date of the session")
    notes = models.TextField(null=True, blank=True)
    souls_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of souls won during this session",
    )
    duration_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Duration of the session in minutes",
    )

    class Meta:
        db_table = "personal_mission_sessions"
        indexes = [
            models.Index(fields=["mission", "date"]),
        ]

    def __str__(self):
        return f"{self.mission.name} - Session on {self.date}"

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "mission_id": self.mission_id,
        })
        return data
