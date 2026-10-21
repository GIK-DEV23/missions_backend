"""Moderation enums.

These mirror, value for value, the unions the clients already declare:
  - missions-web-admin/src/types/moderation.ts
  - souls_app/lib/features/moderation/data/models/moderation_models.dart

The clients defined this contract first (BR-1), so the wire values here are
copied from them rather than invented. Changing a value is a breaking change
for both clients and the admin dashboard.
"""

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ReportReason(TextChoices):
    """Why a reporter flagged the content. Mirrors ContentReportReason."""

    INAPPROPRIATE = "inappropriate", _("Inappropriate content")
    SPAM = "spam", _("Spam")
    HARASSMENT = "harassment", _("Harassment")
    FALSE_INFO = "false_info", _("False information")
    HATE_SPEECH = "hate_speech", _("Hate speech")
    PRIVACY_VIOLATION = "privacy_violation", _("Privacy violation")
    OTHER = "other", _("Other")


class ReportStatus(TextChoices):
    """Review lifecycle of a report. Mirrors ContentReportStatus."""

    PENDING = "pending", _("Pending review")
    UNDER_REVIEW = "under_review", _("Under review")
    RESOLVED_REMOVED = "resolved_removed", _("Removed")
    RESOLVED_NO_ACTION = "resolved_no_action", _("No action taken")
    DISMISSED = "dismissed", _("Dismissed")


#: Statuses that close a report. Used to stamp reviewed_at / reviewed_by.
TERMINAL_REPORT_STATUSES = frozenset({
    ReportStatus.RESOLVED_REMOVED,
    ReportStatus.RESOLVED_NO_ACTION,
    ReportStatus.DISMISSED,
})


class ReportableContentType(TextChoices):
    """What can be reported.

    `highlight` is deliberately absent: the Highlight submission kind is
    deferred on both clients (souls_app removed its compose and view screens,
    and the dashboard dropped it from ContentType), so accepting reports for it
    would create rows nothing can review. Featured testimonies — the thing the
    mobile home screen calls a highlight — are reported as `testimony`, which
    is what they are.
    """

    TESTIMONY = "testimony", _("Testimony")
    MIRACLE = "miracle", _("Miracle")
    SOUL = "soul", _("Soul")
    USER = "user", _("User")


#: Content that `resolved_removed` is meaningful for.
#:
#: A testimony or miracle is published content, so "removed" means taken down.
#: A Soul is a pastoral record about a third party and a User is an account:
#: neither is published, so "removing" one would destroy ministry data or
#: imply an account action that belongs to the deletion lifecycle instead.
#: Reports on those resolve as resolved_no_action or dismissed with a note, and
#: any real action is taken deliberately through its own endpoint.
REMOVABLE_CONTENT_TYPES = frozenset({
    ReportableContentType.TESTIMONY,
    ReportableContentType.MIRACLE,
})


class DeletionStatus(TextChoices):
    """Account erasure lifecycle. Mirrors the DeletionStatus union."""

    ACTIVE = "active", _("Active")
    DELETION_REQUESTED = "deletion_requested", _("Deletion requested")
    IN_GRACE_PERIOD = "in_grace_period", _("Grace period")
    ERASURE_IN_PROGRESS = "erasure_in_progress", _("Erasure in progress")
    ERASURE_COMPLETE = "erasure_complete", _("Deleted")
    LEGAL_HOLD = "legal_hold", _("Legal hold")


#: Days between a deletion request and the earliest erasure.
#: The user can cancel at any point inside this window.
GRACE_PERIOD_DAYS = 30

#: Placeholder written over a deleted user's identifying columns.
ANONYMIZED_NAME = "Deleted user"
