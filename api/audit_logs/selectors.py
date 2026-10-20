from enum import Enum
from typing import Optional

from django.db.models import QuerySet

from audit_logs.filters import AuditLogFilter
from audit_logs.models import AuditLog
from base.utils.exceptions import NotFoundError


def audit_log_details(id: int) -> AuditLog:
    """
    Get details of an audit log entry by ID.

    Args:
        id: ID of the audit log entry.

    Returns:
        AuditLog instance.

    Raises:
        ValueError: If the AuditLog with the given ID does not exist.
    """
    try:
        return AuditLog.objects.get(id=id)
    except AuditLog.DoesNotExist:
        raise NotFoundError("AuditLog with the the id {} does not exist.".format(id))


def audit_logs_list(filters: Optional[dict] = None):
    """
    List all audit log entries.

    Returns:
        List of AuditLog instances.
    """
    qs = AuditLog.objects.all()
    if filters:
        action_type = filters.get("action_type")
        if action_type and isinstance(action_type, Enum):
            filters["action_type"] = action_type.value
        action_category = filters.get("action_category")
        if action_category and isinstance(action_category, Enum):
            filters["action_category"] = action_category.value
    return AuditLogFilter(filters, qs).qs if filters else qs


def moderation_audit_logs(
    content_type: Optional[str] = None,
    content_id: Optional[int] = None,
    action_type: Optional[str] = None,
    moderator_id: Optional[int] = None,
) -> QuerySet:
    """
    Get moderation audit logs with optional filters.

    Args:
        content_type: Filter by content type ('testimony', 'miracle').
        content_id: Filter by specific content ID.
        action_type: Filter by action type ('approve', 'reject').
        moderator_id: Filter by moderator user ID.

    Returns:
        QuerySet of moderation AuditLog entries.
    """
    qs = AuditLog.objects.filter(action_category="moderation")
    
    if content_type:
        qs = qs.filter(content_type=content_type)
    if content_id:
        qs = qs.filter(content_id=content_id)
    if action_type:
        qs = qs.filter(action_type=action_type)
    if moderator_id:
        qs = qs.filter(user_id=moderator_id)
    
    return qs.select_related("user").order_by("-created_at")


def content_moderation_history(content_type: str, content_id: int) -> QuerySet:
    """
    Get the full moderation history for a specific piece of content.

    Args:
        content_type: Type of content ('testimony', 'miracle').
        content_id: ID of the content.

    Returns:
        QuerySet of AuditLog entries for this content, newest first.
    """
    return moderation_audit_logs(content_type=content_type, content_id=content_id)