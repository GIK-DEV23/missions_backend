import logging
from typing import Dict, List, Optional

from django.utils import timezone

from audit_logs.constants import ActionType
from audit_logs.services import log_audit_event
from base.utils.exceptions import CustomValidationError
from notifications.models import Notification
from notifications.selectors import get_notification

logger = logging.getLogger(__name__)

#: Guard against a mistyped broadcast hitting the whole user base in one call.
MAX_BROADCAST_RECIPIENTS = 10000


def create_notification(user, title: str, body: str = "", type: str = None) -> Notification:
    """Enqueue one notification. Used by other apps reacting to events."""
    return Notification.objects.create(user=user, title=title, body=body, type=type)


def mark_notification_read(user, notification_id: int) -> Notification:
    notification = get_notification(user, notification_id)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
    return notification


def mark_all_notifications_read(user) -> int:
    """Clear the caller's whole unread badge in one call."""
    return Notification.objects.filter(user=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )


def _deliverable_users(queryset):
    """Drop recipients a notification must never reach.

    An inactive account cannot read it, and an erased one must not be written
    to at all — the whole point of erasure is that nothing new accrues against
    that user.
    """
    from moderation.constants import DeletionStatus

    return queryset.filter(is_active=True).exclude(
        deletion__status__in=[
            DeletionStatus.ERASURE_IN_PROGRESS,
            DeletionStatus.ERASURE_COMPLETE,
        ]
    )


def _fan_out(sender, recipients, title: str, body: str, type: Optional[str], audience: str) -> Dict:
    notifications = [
        Notification(user=user, title=title, body=body, type=type) for user in recipients
    ]
    created = Notification.objects.bulk_create(notifications)

    log_audit_event(
        user=sender,
        action_type=ActionType.CREATION,
        action_category="notifications",
        action_description="Sent '{}' to {} recipient(s) [{}]".format(
            title[:80], len(created), audience
        ),
        is_successful=True,
    )
    return {"created": len(created), "recipients": len(created)}


def send_notification(sender, user_ids: List[int], title: str, body: str = "",
                      type: Optional[str] = None) -> Dict:
    """Send to a named set of users.

    Ids that cannot be delivered to are reported in `skipped_user_ids` rather
    than failing the call, so one stale id in a list does not lose the rest.
    """
    from users.models import User

    if not user_ids:
        raise CustomValidationError("user_ids must name at least one recipient.")

    requested = set(user_ids)
    recipients = list(_deliverable_users(User.objects.filter(id__in=requested)))
    delivered = {u.pk for u in recipients}

    result = _fan_out(sender, recipients, title, body, type, "direct")
    result["skipped_user_ids"] = sorted(requested - delivered)
    return result


def broadcast_notification(sender, title: str, body: str = "", type: Optional[str] = None,
                           roles: Optional[List[str]] = None,
                           mission_id: Optional[int] = None) -> Dict:
    """Send to an audience resolved server-side.

    Narrows from every active user by role and/or mission registration. Capped
    at MAX_BROADCAST_RECIPIENTS so a mistyped filter cannot fan out to the
    entire user base silently.
    """
    from users.models import User

    queryset = User.objects.all()
    audience_parts = []

    if roles:
        queryset = queryset.filter(roles__name__in=roles)
        audience_parts.append("roles={}".format(",".join(roles)))
    if mission_id is not None:
        queryset = queryset.filter(jia_participations__mission_id=mission_id)
        audience_parts.append("mission={}".format(mission_id))
    if not audience_parts:
        audience_parts.append("all active users")

    recipients = list(_deliverable_users(queryset).distinct())

    if len(recipients) > MAX_BROADCAST_RECIPIENTS:
        raise CustomValidationError(
            "This would notify {} users, above the {} cap. Narrow the audience "
            "with roles or mission_id.".format(len(recipients), MAX_BROADCAST_RECIPIENTS)
        )
    if not recipients:
        raise CustomValidationError("That audience resolves to no deliverable recipients.")

    result = _fan_out(sender, recipients, title, body, type, "; ".join(audience_parts))
    result["skipped_user_ids"] = []
    return result
