from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class SubmissionVisibility(TextChoices):
    PUBLIC = "public", _("Public")
    ANONYMOUS = "anonymous", _("Anonymous")
    PRIVATE = "private", _("Private")


class ReviewStatus(TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
