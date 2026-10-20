from django.core.cache import cache

from audit_logs.models import AuditLog
from audit_logs.constants import ActionType, ContentType
from audit_logs.selectors import audit_log_details


def log_audit_event(user, action_type, action_category, action_description, is_successful, ip_address=None, flag_suspicious=False):
    """
    Create an audit log entry.

    Args:
        user: User instance performing the action.
        action_type: Type of action performed.
        action_category: Category of the action.
        action_description: Description of the action.
        is_successful: Boolean indicating if the action was successful.
        ip_address: Optional IP address from which the action was performed.
        flag_suspicious: Boolean indicating if the action is suspicious.

    Returns:
        The created AuditLog instance.
    """
    if ip_address is None:
        ip_address=cache.get("user_ip_{}".format(user.id))

    audit_log = AuditLog.objects.create(
        user=user,
        action_type=action_type,
        action_category=action_category,
        action_description=action_description,
        is_successful=is_successful,
        ip_address=ip_address,
        flag_suspicious=flag_suspicious
    )
    return audit_log


def log_moderation_action(
    user,
    action_type: str,
    content_type: str,
    content_id: int,
    content_title: str,
    previous_status: str,
    new_status: str,
    rejection_reason: str = None,
    ip_address=None
):
    """
    Create a moderation audit log entry.

    Args:
        user: User instance performing the moderation action.
        action_type: ActionType.APPROVE, ActionType.REJECT, etc.
        content_type: ContentType.TESTIMONY, ContentType.MIRACLE.
        content_id: ID of the content being moderated.
        content_title: Title of the content (for description).
        previous_status: Review status before this action.
        new_status: Review status after this action.
        rejection_reason: Optional reason for rejection.
        ip_address: Optional IP address.

    Returns:
        The created AuditLog instance.
    """
    if ip_address is None:
        ip_address = cache.get("user_ip_{}".format(user.id))

    action_verb = "approved" if action_type == ActionType.APPROVE else "rejected"
    description = f"{action_verb.capitalize()} {content_type} #{content_id}: {content_title[:50]}"
    if rejection_reason:
        description = f"{description} - Reason: {rejection_reason[:100]}"

    audit_log = AuditLog.objects.create(
        user=user,
        action_type=action_type,
        action_category="moderation",
        action_description=description,
        is_successful=True,
        ip_address=ip_address,
        flag_suspicious=False,
        content_type=content_type,
        content_id=content_id,
        previous_status=previous_status,
        new_status=new_status,
        rejection_reason=rejection_reason
    )
    return audit_log


def flag_suspicious_log(audit_log_id: int):
    """
    Flag an existing audit log entry as suspicious.

    Args:
        audit_log_id: ID of the AuditLog entry to flag.
    Returns:
        The updated AuditLog instance.
    """
    audit_log = audit_log_details(audit_log_id)
    audit_log.flag_suspicious = True
    audit_log.save()
    return audit_log


def unflag_suspicious_log(audit_log_id: int):
    """
    Unflag an existing audit log entry as suspicious.

    Args:
        audit_log_id: ID of the AuditLog entry to unflag.
    Returns:
        The updated AuditLog instance.
    """
    audit_log = audit_log_details(audit_log_id)
    audit_log.flag_suspicious = False
    audit_log.save()
    return audit_log
