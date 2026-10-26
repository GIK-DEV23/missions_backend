from typing import Optional

from typing import Optional

from django.db import models
from django.http import HttpRequest
from phonenumber_field.modelfields import PhoneNumberField

from base.models import BaseModel, client_id_field
from souls.constants import JourneyStage, ContactOutcome, ProgressUpdateType, ProgressUpdateOutcome, GuardianRelationship
from users.constants import GenderType, AgeGroupCategory


class Soul(BaseModel):
    client_id = client_id_field()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, default="")
    phone_number = PhoneNumberField()
    location = models.ForeignKey("missions.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name='souls')
    status = models.CharField(max_length=50, choices=JourneyStage.choices, default=JourneyStage.NEW_BELIEVER)
    contact_outcome = models.CharField(max_length=30, choices=ContactOutcome.choices, null=True, blank=True)
    date_added = models.DateField()
    mission = models.ForeignKey("missions.Mission", on_delete=models.PROTECT, null=True, blank=True, related_name='souls')
    personal_mission = models.ForeignKey("personal_missions.PersonalMission", on_delete=models.SET_NULL, null=True, blank=True, related_name='souls')
    is_personal = models.BooleanField(default=False)
    user = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name='souls')
    description = models.CharField(max_length=250, null=True, blank=True)
    gender = models.CharField(max_length=50, choices=GenderType.choices)
    age_group = models.CharField(max_length=30, choices=AgeGroupCategory.choices)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    next_check_in_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True, help_text="Derived from progress updates, never written directly")
    consent_given = models.BooleanField(default=False)
    consent_recorded_at = models.DateTimeField(null=True, blank=True)
    do_not_contact = models.BooleanField(default=False)
    do_not_contact_at = models.DateTimeField(null=True, blank=True)
    possible_duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='possible_duplicates')
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Tombstone, set when merged into another soul")

    # Guardian consent fields for minors (age_group in {0-12, 13-17})
    guardian_name = models.CharField(max_length=150, null=True, blank=True)
    guardian_relationship = models.CharField(
        max_length=20,
        choices=GuardianRelationship.choices,
        null=True,
        blank=True
    )
    guardian_consent_given = models.BooleanField(default=False)
    guardian_consent_date = models.DateTimeField(null=True, blank=True)
    guardian_phone = PhoneNumberField(null=True, blank=True)

    class Meta:
        db_table = "souls"
        indexes = [
            models.Index(fields=['phone_number']),
        ]
        unique_together = ('first_name', 'last_name', 'phone_number', 'user', 'mission')

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name).strip()

    def __str__(self):
        return self.get_full_name()

    def to_dict(self, request: Optional[HttpRequest] = None, mask_phone: bool = False):
        from souls.selectors import compute_follow_up_health
        from souls.utils import mask_phone_number
        
        data = super().to_dict()
        
        # Apply phone masking if requested
        if mask_phone:
            data['phone_number'] = mask_phone_number(data.get('phone_number'))
            data['phone_number_masked'] = True
        else:
            data['phone_number_masked'] = False
        
        guardian_phone_value = str(self.guardian_phone) if self.guardian_phone else None
        if mask_phone and guardian_phone_value:
            guardian_phone_value = mask_phone_number(guardian_phone_value)
        
        data.update({
            "location_id": self.location.id if self.location else None,
            "location_name": self.location.name if self.location else None,
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "personal_mission_id": self.personal_mission.id if self.personal_mission else None,
            "personal_mission_client_id": str(self.personal_mission.client_id) if self.personal_mission and self.personal_mission.client_id else None,
            "possible_duplicate_of": self.possible_duplicate_of_id,
            "user_id": self.user.id if self.user else None,
            "user_full_name": str(self.user.get_full_name()) if self.user else None,
            "soul_full_name": self.get_full_name(),
            "follow_up_health": compute_follow_up_health(self),
            # Guardian consent fields for minors
            "guardian_name": self.guardian_name,
            "guardian_relationship": self.guardian_relationship,
            "guardian_consent_given": self.guardian_consent_given,
            "guardian_consent_date": self.guardian_consent_date.isoformat() if self.guardian_consent_date else None,
            "guardian_phone": guardian_phone_value,
        })
        return data

    def to_dict_details(self, request: Optional[HttpRequest] = None, mask_phone: bool = False):
        data = self.to_dict(request, mask_phone=mask_phone)
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
    author = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_progress_updates')
    content = models.TextField()
    update_date = models.DateField()
    type = models.CharField(max_length=20, choices=ProgressUpdateType.choices, null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=ProgressUpdateOutcome.choices, null=True, blank=True)
    next_check_in_at = models.DateTimeField(null=True, blank=True)

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
            "author_id": self.author.id if self.author else None,
            "author_full_name": str(self.author.get_full_name()) if self.author else None,
        })
        return data


class SoulAssignment(BaseModel):
    soul = models.ForeignKey(Soul, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name='soul_assignments')
    assigned_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_souls')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "soul_assignments"
        indexes = [
            models.Index(fields=['soul', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return "{} assigned to {}".format(self.soul.get_full_name(), self.user.get_full_name())

    def to_dict(self, request: Optional[HttpRequest] = None):
        data = super().to_dict()
        data.update({
            "soul_id": self.soul_id,
            "soul_full_name": self.soul.get_full_name(),
            "user_id": self.user_id,
            "user_full_name": str(self.user.get_full_name()),
            "assigned_by_id": self.assigned_by_id,
            "assigned_by_full_name": str(self.assigned_by.get_full_name()) if self.assigned_by else None,
            "is_active": self.is_active,
            "notes": self.notes,
        })
        return data