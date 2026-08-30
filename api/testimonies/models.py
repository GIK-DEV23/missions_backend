import os
from typing import Dict, Any

from django.db import models
from django.http import HttpRequest
from django.utils import timezone

from base.models import BaseModel, client_id_field
from testimonies.constants import SubmissionVisibility, ReviewStatus


def get_testimonies_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    return os.path.join("testimonies", "photos", "{}{}".format(timestamp, ext))


def get_miracles_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    return os.path.join("miracles", "photos", "{}{}".format(timestamp, ext))


def get_highlights_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    return os.path.join("highlights", "photos", "{}{}".format(timestamp, ext))



class Testimony(BaseModel):
    """Model to store testimonies"""
    client_id = client_id_field()
    title = models.CharField(
        max_length=255,
        help_text="Title of the testimony",
    )
    content = models.TextField(
        help_text="Content of the testimony",
    )
    soul = models.ForeignKey(
        "souls.Soul",
        on_delete=models.CASCADE,
        related_name="testimonies",
        help_text="The soul associated with this testimony",
        null = True,
        blank = True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="testimonies",
        help_text="The user who submitted the testimony",
        null=True,
        blank=True,
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="testimonies",
        help_text="The mission associated with this testimony",
        null = True,
        blank = True,
    )
    personal_mission = models.ForeignKey(
        "personal_missions.PersonalMission",
        on_delete=models.SET_NULL,
        related_name="testimonies",
        help_text="The personal mission associated with this testimony",
        null=True,
        blank=True,
    )
    is_personal = models.BooleanField(default=False)
    photo = models.ImageField(
        upload_to=get_testimonies_dir,
        null=True,
        blank=True,
        help_text="Optional photo associated with the testimony",
    )
    is_selected = models.BooleanField(
        default=False,
        help_text="Indicates whether the testimony has been selected for publication",
    )
    visibility = models.CharField(max_length=20, choices=SubmissionVisibility.choices, default=SubmissionVisibility.PUBLIC)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    rejection_reason = models.TextField(null=True, blank=True)
    third_party_consent = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Testimony"
        verbose_name_plural = "Testimonies"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Testimony by {self.soul} - {self.title}"

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "soul_id": self.soul.id if self.soul else None,
            "soul_full_name": self.soul.get_full_name() if self.soul else None,
            "user_id": self.user.id if self.user else None,
            "user_full_name": str(self.user.get_full_name()) if self.user else None,
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "personal_mission_id": self.personal_mission.id if self.personal_mission else None,
            "photo_url": request.build_absolute_uri(self.photo.url) if self.photo and request else None,
        })
        return data


class Miracle(BaseModel):
    client_id = client_id_field()
    title = models.CharField(
        max_length=255,
        help_text="Title of the miracle",
    )
    content = models.TextField(
        help_text="Content of the miracle",
    )
    photo = models.ImageField(
        upload_to=get_testimonies_dir,
        null=True,
        blank=True,
        help_text="Optional photo associated with the miracle",
    )
    soul = models.ForeignKey(
        "souls.Soul",
        on_delete=models.CASCADE,
        related_name="miracles",
        help_text="The soul associated with this miracle",
        null = True,
        blank = True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="miracles",
        help_text="The user who submitted the miracle",
        null=True,
        blank=True,
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="miracles",
        help_text="The mission associated with this miracle",
        null = True,
        blank = True,
    )
    personal_mission = models.ForeignKey(
        "personal_missions.PersonalMission",
        on_delete=models.SET_NULL,
        related_name="miracles",
        help_text="The personal mission associated with this miracle",
        null=True,
        blank=True,
    )
    is_personal = models.BooleanField(default=False)
    is_selected = models.BooleanField(
        default=False,
        help_text="Indicates whether the miracle has been selected",
    )
    visibility = models.CharField(max_length=20, choices=SubmissionVisibility.choices, default=SubmissionVisibility.PUBLIC)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    rejection_reason = models.TextField(null=True, blank=True)
    third_party_consent = models.BooleanField(default=False)

    def __str__(self):
        return f"Miracle by {self.soul} - {self.title}"

    class Meta:
        verbose_name = "Miracle"
        verbose_name_plural = "Miracles"
        ordering = ["-created_at"]

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "soul_id": self.soul.id if self.soul else None,
            "soul_full_name": self.soul.get_full_name() if self.soul else None,
            "user_id": self.user.id if self.user else None,
            "user_full_name": str(self.user.get_full_name()) if self.user else None,
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "personal_mission_id": self.personal_mission.id if self.personal_mission else None,
            "photo_url": request.build_absolute_uri(self.photo.url) if self.photo and request else None,
        })
        return data


class Highlight(BaseModel):
    """Third submission table, same shape as Testimony/Miracle (no is_selected — that stays Testimony-only)."""
    client_id = client_id_field()
    title = models.CharField(max_length=255, help_text="Title of the highlight")
    content = models.TextField(help_text="Content of the highlight")
    photo = models.ImageField(upload_to=get_highlights_dir, null=True, blank=True, help_text="Optional photo associated with the highlight")
    soul = models.ForeignKey(
        "souls.Soul",
        on_delete=models.CASCADE,
        related_name="highlights",
        help_text="The soul associated with this highlight",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="highlights",
        help_text="The user who submitted the highlight",
        null=True,
        blank=True,
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="highlights",
        help_text="The mission associated with this highlight",
        null=True,
        blank=True,
    )
    personal_mission = models.ForeignKey(
        "personal_missions.PersonalMission",
        on_delete=models.SET_NULL,
        related_name="highlights",
        help_text="The personal mission associated with this highlight",
        null=True,
        blank=True,
    )
    is_personal = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=SubmissionVisibility.choices, default=SubmissionVisibility.PUBLIC)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    rejection_reason = models.TextField(null=True, blank=True)
    third_party_consent = models.BooleanField(default=False)

    def __str__(self):
        return f"Highlight by {self.soul} - {self.title}"

    class Meta:
        verbose_name = "Highlight"
        verbose_name_plural = "Highlights"
        ordering = ["-created_at"]

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "soul_id": self.soul.id if self.soul else None,
            "soul_full_name": self.soul.get_full_name() if self.soul else None,
            "user_id": self.user.id if self.user else None,
            "user_full_name": str(self.user.get_full_name()) if self.user else None,
            "mission_id": self.mission.id if self.mission else None,
            "mission_title": self.mission.title if self.mission else None,
            "personal_mission_id": self.personal_mission.id if self.personal_mission else None,
            "photo_url": request.build_absolute_uri(self.photo.url) if self.photo and request else None,
        })
        return data
