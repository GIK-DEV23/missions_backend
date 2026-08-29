from typing import Optional

from django.db import models
from django.http import HttpRequest
from phonenumber_field.modelfields import PhoneNumberField

from base.models import BaseModel, client_id_field
from souls.constants import JourneyStage, ContactOutcome
from users.constants import GenderType, AgeGroupCategory


class Soul(BaseModel):
    client_id = client_id_field()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = PhoneNumberField()
    location = models.ForeignKey("missions.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name='souls')
    status = models.CharField(max_length=50, choices=JourneyStage.choices, default=JourneyStage.NEW_BELIEVER)
    contact_outcome = models.CharField(max_length=30, choices=ContactOutcome.choices, null=True, blank=True)
    date_added = models.DateField()
    mission = models.ForeignKey("missions.Mission", on_delete=models.PROTECT, null=True, blank=True, related_name='souls')
    is_personal = models.BooleanField(default=False)
    user = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name='souls')
    description = models.CharField(max_length=250, null=True, blank=True)
    gender = models.CharField(max_length=50, choices=GenderType.choices)
    age_group = models.CharField(max_length=30, choices=AgeGroupCategory.choices)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "souls"
        indexes = [
            models.Index(fields=['phone_number']),
        ]
        unique_together = ('first_name', 'last_name', 'phone_number', 'user', 'mission')

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def __str__(self):
        return self.get_full_name()

    def to_dict(self, request: Optional[HttpRequest] = None):
        data = super().to_dict()
        data.update({
            "location_id": self.location.id if self.location else None,
            "location_name": self.location.name if self.location else None,
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "user_id": self.user.id if self.user else None,
            "user_full_name": str(self.user.get_full_name()) if self.user else None,
            "soul_full_name": self.get_full_name()
        })
        return data

    def to_dict_details(self, request: Optional[HttpRequest] = None):
        data = self.to_dict(request)
        # get first and last progress update
        progress_updates = self.progress_updates.all().order_by('-update_date', '-created_at')
        if not progress_updates.exists():
            data['latest_progress_update'] = None
            data['initial_progress_update'] = None
        elif progress_updates.count() == 1:
            progress_update = progress_updates.first()
            data['latest_progress_update'] = progress_update.to_dict(request)
            data['initial_progress_update'] = progress_update.to_dict(request)
        else:
            first_progress_update = progress_updates.first()
            last_progress_update = progress_updates.last()
            data['latest_progress_update'] = first_progress_update.to_dict(request)
            data['initial_progress_update'] = last_progress_update.to_dict(request)
        return data


class ProgressUpdate(BaseModel):
    client_id = client_id_field()
    soul = models.ForeignKey(Soul, on_delete=models.CASCADE, related_name='progress_updates')
    content = models.TextField()
    update_date = models.DateField()

    class Meta:
        db_table = "soul_progress_updates"
        ordering = ['-update_date']

    def __str__(self):
        return "Progress Update for {} on {}".format(self.soul.get_full_name(), self.update_date)

    def to_dict(self, request: models.Model = None):
        data = super().to_dict()
        data.update({
            "soul_id": self.soul.id if self.soul else None,
            "soul_full_name": self.soul.get_full_name() if self.soul else None,
        })
        return data