from django.utils import timezone

from notifications.models import Notification
from notifications.selectors import get_notification


def create_notification(user, title: str, body: str = "", type: str = None) -> Notification:
    """Internal utility for other apps to enqueue a notification.

    No creation trigger is wired up anywhere yet — GIK-02 doesn't specify
    whether the client ever creates notifications directly or the server
    generates them from events, so nothing calls this yet. It exists so a
    future ticket can call it without redesigning this app.
    """
    return Notification.objects.create(user=user, title=title, body=body, type=type)


def mark_notification_read(user, notification_id: int) -> Notification:
    notification = get_notification(user, notification_id)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
    return notification
