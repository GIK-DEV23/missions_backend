from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class LocationCategoryType(TextChoices):
    """Location category choices"""
    COUNTRY = "country", _("Country")
    COUNTY = "county", _("County")
    TOWN = "town", _("Town")


class MissionStatusType(TextChoices):
    """Mission status choices"""
    PLANNING = "planning", _("Planning")
    ACTIVE = "active", _("Active")
    COMPLETED = "completed", _("Completed")
    ON_HOLD = "on_hold", _("On Hold")


class EventType(TextChoices):
    """Event type choices"""
    ONE_DAY = "one_day", _("One Day")
    WEEK_LONG = "week_long", _("Week Long")


class PaymentTiming(TextChoices):
    """When a participant intends to pay their registration fee"""
    MPESA_NOW = "mpesa_now", _("M-Pesa now")
    PAY_LATER = "pay_later", _("Pay later")
    ON_ARRIVAL = "on_arrival", _("On arrival")
