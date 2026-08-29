from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class JourneyStage(TextChoices):
    NOT_YET_SAVED = "not_yet_saved", _("Not yet saved")
    NEW_BELIEVER = "new_believer", _("New believer")
    GROWING = "growing", _("Growing")
    ROOTED = "rooted", _("Rooted")
    IN_A_CHURCH = "in_a_church", _("In a church")


class ContactOutcome(TextChoices):
    BORN_AGAIN = "born_again", _("Born again")
    ALREADY_BELIEVER = "already_believer", _("Already believer")
    NOT_YET = "not_yet", _("Not yet")
