from base.utils.exceptions import NotFoundError
from notifications.models import Notification


def get_notification(user, notification_id: int) -> Notification:
    try:
        return Notification.objects.get(id=notification_id, user=user)
    except Notification.DoesNotExist:
        raise NotFoundError("Notification with ID {} does not exist".format(notification_id))


def list_notifications(user):
    return Notification.objects.filter(user=user)
