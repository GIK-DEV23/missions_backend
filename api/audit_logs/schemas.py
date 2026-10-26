from enum import Enum
from typing import Optional

from ninja import Schema

from base.schemas import BaseOut, BaseQuery


class AuditLogSchema(BaseOut):
    user_id: int
    user_name: Optional[str] = None
    action_type: str
    action_category: str
    action_description: str
    is_successful: bool
    ip_address: str | None = None
    flag_suspicious: bool
    # Moderation-specific fields
    content_type: Optional[str] = None
    content_id: Optional[int] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    rejection_reason: Optional[str] = None


class ActionType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CREATION = "creation"
    MODIFICATION = "modification"
    DELETION = "deletion"
    REPORTS = "reports"
    # Moderation actions
    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"
    UNFLAG = "unflag"


class ActionCategory(str, Enum):
    AUTHENTICATION = "authentication"
    SOULS = "souls"
    LOCATIONS = "locations"
    MISSION_CATEGORIES = "mission_categories"
    MISSIONS = "missions"
    USERS = "users"
    REPORTS = "reports"
    MODERATION = "moderation"


class ContentType(str, Enum):
    TESTIMONY = "testimony"
    MIRACLE = "miracle"


class AuditLogQueryIn(BaseQuery):
    user_id: int | None = None
    action_type: ActionType | None = None
    action_category: ActionCategory | None = None
    is_successful: bool | None = None
    flag_suspicious: bool | None = None
    ip_address: str | None = None


class ModerationAuditQueryIn(BaseQuery):
    """Query parameters for moderation audit logs"""
    content_type: Optional[ContentType] = None
    content_id: Optional[int] = None
    action_type: Optional[ActionType] = None
    moderator_id: Optional[int] = None
