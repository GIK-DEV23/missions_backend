from typing import Optional

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
