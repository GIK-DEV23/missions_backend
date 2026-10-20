from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ActionType(TextChoices):
    '''
    1. Delete soul, mission, user
    2. Create staff, location, or mission category
    3. Edit staff, location or mission category
    4. Login/Logout
    5. Content moderation (approve/reject)
    '''
    LOGIN = "login", _("Login")
    LOGOUT = "logout", _("Logout")
    CREATION = "creation", _("Creation")
    MODIFICATION = "modification", _("Modification")
    DELETION = "deletion", _("Deletion")
    REPORTS = "reports", _("Reports")
    # Moderation actions
    APPROVE = "approve", _("Approve")
    REJECT = "reject", _("Reject")
    FLAG = "flag", _("Flag")
    UNFLAG = "unflag", _("Unflag")


ACTION_CATEGORIES = [
    "authentication", "souls", "locations", "mission_categories", "missions", "users", "reports",
    "moderation"
]


class ContentType(TextChoices):
    """Content types that can be moderated"""
    TESTIMONY = "testimony", _("Testimony")
    MIRACLE = "miracle", _("Miracle")