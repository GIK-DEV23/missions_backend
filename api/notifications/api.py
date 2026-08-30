from django.http import JsonResponse
from ninja import Router, Query

from authentication.permissions import jwt_auth
from authentication.decorators import require_permission
from base.api import paginate_response
from base.schemas import DetailOut
from notifications import schemas, services, selectors

router = Router(tags=["notifications"])


@require_permission("list_notifications")
@router.get(
    "/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
def notifications_list_api(request, params: schemas.NotificationsQuery = Query(...)):
    """Owner-scoped list of the caller's own notifications."""
    notifications = selectors.list_notifications(user=request.user)
    if params.is_read is not None:
        notifications = notifications.filter(is_read=params.is_read)
    response = paginate_response(
        queryset=notifications,
        request=request,
        schema=schemas.NotificationOut,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@require_permission("mark_notification_read")
@router.post(
    "/{notification_id}/read/",
    response={200: schemas.NotificationOut, 400: DetailOut},
    auth=jwt_auth
)
def mark_notification_read_api(request, notification_id: int):
    notification = services.mark_notification_read(user=request.user, notification_id=notification_id)
    return 200, schemas.NotificationOut(**notification.to_dict(request))
