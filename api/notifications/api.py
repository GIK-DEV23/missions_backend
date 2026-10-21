from django.http import JsonResponse
from ninja import Router, Query

from authentication.permissions import jwt_auth
from authentication.decorators import require_permission
from base.api import paginate_response
from base.schemas import DetailOut
from notifications import schemas, services, selectors

router = Router(tags=["notifications"])


@router.get(
    "/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_notifications")
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


@router.post(
    "/read-all/",
    response={200: DetailOut},
    auth=jwt_auth
)
@require_permission("mark_notification_read")
def mark_all_notifications_read_api(request):
    """Clear the caller's whole unread badge in one call."""
    count = services.mark_all_notifications_read(user=request.user)
    return 200, DetailOut(detail="Marked {} notification(s) as read".format(count))


# ─── Composing notifications (BR-3) ───────────────────────────────────────────
# Registered before /{notification_id}/ so these literal paths are never
# shadowed by the id route.

@router.post(
    "/send/",
    response={201: schemas.NotificationSendOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("send_notification")
def send_notification_api(request, body: schemas.NotificationSendIn):
    """Send one notification to a named set of users.

    Undeliverable ids (inactive or erased accounts, or ids that do not exist)
    come back in `skipped_user_ids` rather than failing the whole call.
    """
    result = services.send_notification(
        sender=request.user,
        user_ids=body.user_ids,
        title=body.title,
        body=body.body,
        type=body.type,
    )
    return 201, schemas.NotificationSendOut(**result)


@router.post(
    "/broadcast/",
    response={201: schemas.NotificationSendOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("broadcast_notification")
def broadcast_notification_api(request, body: schemas.NotificationBroadcastIn):
    """Send one notification to an audience the server resolves.

    Narrows from every active user by `roles` and/or `mission_id`. An empty
    payload means every active user, which is why this needs its own
    permission and is capped server-side.
    """
    result = services.broadcast_notification(
        sender=request.user,
        title=body.title,
        body=body.body,
        type=body.type,
        roles=body.roles,
        mission_id=body.mission_id,
    )
    return 201, schemas.NotificationSendOut(**result)


@router.get(
    "/{notification_id}/",
    response={200: schemas.NotificationOut, 404: DetailOut},
    auth=jwt_auth
)
@require_permission("list_notifications")
def notification_details_api(request, notification_id: int):
    """One notification, owner-scoped.

    The mobile client already references this route; it did not exist before.
    """
    notification = selectors.get_notification(request.user, notification_id)
    return 200, schemas.NotificationOut(**notification.to_dict(request))


@router.post(
    "/{notification_id}/read/",
    response={200: schemas.NotificationOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("mark_notification_read")
def mark_notification_read_api(request, notification_id: int):
    notification = services.mark_notification_read(user=request.user, notification_id=notification_id)
    return 200, schemas.NotificationOut(**notification.to_dict(request))
