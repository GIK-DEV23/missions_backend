from enum import Enum
from typing import Optional

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