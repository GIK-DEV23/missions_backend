from typing import List, Optional

from ninja import Schema

from base.schemas import BaseOut, BaseQuery


class NotificationsQuery(BaseQuery):
    is_read: Optional[bool] = None


class NotificationOut(BaseOut):
    user_id: int
    title: str
    body: str
    type: Optional[str] = None
    is_read: bool = False
    read_at: Optional[str] = None


# ─── Composing notifications (BR-3) ───────────────────────────────────────────

class NotificationSendIn(Schema):
    """Send one notification to a named set of users."""

    user_ids: List[int]
    title: str
    body: str = ""
    type: Optional[str] = None


class NotificationBroadcastIn(Schema):
    """Send one notification to an audience the server resolves.

    The audience narrows from every active user: `roles` restricts to holders
    of those roles, `mission_id` to that mission's registered participants, and
    both together to the intersection. An empty payload therefore means
    "every active user", which is deliberate but wide — the endpoint requires
    its own permission for that reason.
    """

    title: str
    body: str = ""
    type: Optional[str] = None
    roles: Optional[List[str]] = None
    mission_id: Optional[int] = None


class NotificationSendOut(Schema):
    created: int
    recipients: int
    skipped_user_ids: List[int] = []
