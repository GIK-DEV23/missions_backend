from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class PersonalMissionType(TextChoices):
    ONE_TIME = "one_time", _("One time")
    ONGOING = "ongoing", _("Ongoing")


class PersonalMissionRhythm(TextChoices):
    WEEKLY = "weekly", _("Weekly")
    FORTNIGHTLY = "fortnightly", _("Fortnightly")
    MONTHLY = "monthly", _("Monthly")
    NONE = "none", _("None")
