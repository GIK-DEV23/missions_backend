import os
from datetime import datetime
from typing import Optional, Dict, Any

from django.db import models
from django.http import HttpRequest
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from base.models import BaseModel
from base.utils.exceptions import CustomValidationError
from missions.constants import LocationCategoryType, MissionStatusType, EventType
from missions.schemas import AttendanceDayOut
from users.constants import GenderType

from base.utils.helpers import commas


def get_reports_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    title = instance.title.strip().replace(" ", "_").lower()
    return os.path.join("missions", "reports", title, "{}{}".format(timestamp, ext))


def get_gallery_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    return os.path.join("missions", "gallery", "{}{}".format(timestamp, ext))


def get_missions_banner_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    return os.path.join("missions", "banners", "{}{}".format(timestamp, ext))


class Location(BaseModel):
    name = models.CharField(max_length=100)
    category = models.CharField(choices=LocationCategoryType.choices, max_length=20)
    description = models.CharField(max_length=255)
    parent_location = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_locations'
    )

    def __str__(self):
        return "{}, {}".format(self.name, self.parent_location) if self.parent_location else self.name

    class Meta:
        db_table = 'locations'

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "parent_location_id": self.parent_location.id if self.parent_location else None,
            "parent_location_name": self.parent_location.name if self.parent_location else None,
        })
        return data


class MissionCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=100, blank=True, null=True, choices=EventType.choices)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'mission_categories'


class Mission(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(MissionCategory, on_delete=models.PROTECT, related_name='missions')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='missions')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(choices=MissionStatusType.choices, max_length=20, default=MissionStatusType.PLANNING)
    partnering_organization = models.JSONField(default=list, help_text="List of partnering organizations")
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='created_missions')
    registration_close_date = models.DateField(null=True, blank=True)
    registration_fee_required = models.BooleanField(default=True)
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    couple_registration_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    banner_image = models.ImageField(upload_to=get_missions_banner_dir, null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def is_registration_open(self) -> bool:
        if self.registration_close_date:
            return timezone.now().date() <= self.registration_close_date
        return True

    @property
    def total_souls_won(self):
        return getattr(self, "souls_won_count", 0)

    @property
    def total_souls_follow_up(self):
        return getattr(self, "souls_followup_count", 0)

    def to_dict(self, request: Optional[HttpRequest] = None):
        data = super().to_dict()
        data.update({
            "category_id": self.category.id if self.category else None,
            "category_name": self.category.name if self.category else None,
            "event_type": self.category.event_type if self.category else None,
            "location_id": self.location.id if self.location else None,
            "location_name": self.location.name if self.location else None,
            "created_by_id": self.created_by.id if self.created_by else None,
            "created_by_name": str(self.created_by) if self.created_by else None,
            "partnering_organization": self.partnering_organization or [],
            "is_registration_open": self.is_registration_open,
            "total_souls_won": commas(self.total_souls_won, use_decimal=False),
            "total_souls_follow_up": commas(self.total_souls_follow_up, use_decimal=False),
            "banner_image": request.build_absolute_uri(self.banner_image.url) if request and self.banner_image else None
        })
        return data

    class Meta:
        db_table = 'missions'
        ordering = ['-start_date']
        unique_together = ('category', 'title', 'start_date', 'location')


class MissionJIAParticipant(BaseModel):
    mission = models.ForeignKey(Mission, on_delete=models.PROTECT, related_name='participants')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='jia_participations')
    full_name = models.CharField(max_length=100)
    travelling_from = models.CharField(max_length=100, help_text="City and Country")
    diet_advisory = models.TextField(blank=True, help_text="Dietary restrictions or advisories")
    days_of_attendance = models.JSONField(default=list, help_text="List of days attending and time")
    need_facilitation = models.BooleanField(default=False, help_text="Need facilitation")
    facilitation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Facilitation amount if needs facilitation")
    coming_as_couple = models.BooleanField(default=False, help_text="Coming as a couple")
    partner_name = models.CharField(max_length=100, blank=True, help_text="Partner's full name if coming as a couple")
    phone_number = PhoneNumberField()
    gender = models.CharField(choices=GenderType.choices, max_length=20)

    def __str__(self):
        return f"{self.phone_number} - {self.full_name}"

    class Meta:
        db_table = 'mission_jia_participants'
        unique_together = ('mission', 'full_name', 'phone_number')

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "user_id": self.user.id if self.user else None,
            "phone_number": str(self.phone_number),
            "days_of_attendance": [
                AttendanceDayOut(
                    **attendance_day
                ) for attendance_day in self.days_of_attendance
            ] or [],
        })
        return data


class Report(BaseModel):
    mission = models.ForeignKey(Mission, on_delete=models.PROTECT, related_name='reports')
    title = models.CharField(max_length=200)
    content = models.TextField()
    report_file = models.FileField(upload_to=get_reports_dir, null=True, blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='created_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "mission_id": self.mission.id if self.mission else None,
            "created_by_id": self.created_by.id if self.created_by else None,
            "created_by_name": str(self.created_by) if self.created_by else None,
        })
        return data


class MissionGallery(BaseModel):
    mission = models.ForeignKey(Mission, on_delete=models.PROTECT, related_name='galleries')
    title = models.CharField(max_length=200, null=True, blank=True)
    image = models.ImageField(upload_to=get_gallery_dir)
    description = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey('users.User', related_name='uploaded_images', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'mission_galleries'
        ordering = ['-created_at']

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "mission_id": self.mission.id if self.mission else None,
            "uploaded_by_id": self.uploaded_by.id if self.uploaded_by else None,
            "image_url": request.build_absolute_uri(self.image.url) if request and self.image else None
        })
        return data
