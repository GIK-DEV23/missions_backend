from typing import List, Optional

from django.http import JsonResponse
from ninja import Router, Query

from audit_logs import schemas
from audit_logs.selectors import audit_log_details, audit_logs_list, moderation_audit_logs, content_moderation_history
from audit_logs.services import flag_suspicious_log, unflag_suspicious_log
from authentication.decorators import require_permission
from authentication.permissions import jwt_auth
from base.api import paginate_response
from base.schemas import DetailOut

router = Router(tags=["audit_logs"])


@router.get(
    "/",
    auth=jwt_auth,
    response={200: List[schemas.AuditLogSchema], 400: DetailOut},
)
@require_permission("list_auditlogs")
def list_audit_logs(request, filters: schemas.AuditLogQueryIn = Query(...)):
    """
    List all audit log entries with optional filters.
    """
    audit_logs = audit_logs_list(filters.dict())
    response = paginate_response(
        request=request,
        queryset=audit_logs,
        schema=schemas.AuditLogSchema,
        page_size=filters.page_size,
        page=filters.page,
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/moderation/",
    auth=jwt_auth,
    response={200: List[schemas.AuditLogSchema], 400: DetailOut},
)
@require_permission("list_auditlogs")
def list_moderation_audit_logs(request, filters: schemas.ModerationAuditQueryIn = Query(...)):
    """
    List moderation audit logs with optional filters.
    
    Filters:
    - content_type: Filter by 'testimony' or 'miracle'
    - content_id: Filter by specific content ID
    - action_type: Filter by 'approve' or 'reject'
    - moderator_id: Filter by moderator user ID
    """
    audit_logs = moderation_audit_logs(
        content_type=filters.content_type.value if filters.content_type else None,
        content_id=filters.content_id,
        action_type=filters.action_type.value if filters.action_type else None,
        moderator_id=filters.moderator_id,
    )
    response = paginate_response(
        request=request,
        queryset=audit_logs,
        schema=schemas.AuditLogSchema,
        page_size=filters.page_size,
        page=filters.page,
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/moderation/content/{content_type}/{content_id}/",
    auth=jwt_auth,
    response={200: List[schemas.AuditLogSchema], 400: DetailOut},
)
@require_permission("list_auditlogs")
def content_moderation_history_api(request, content_type: str, content_id: int):
    """
    Get the full moderation history for a specific piece of content.
    
    Args:
        content_type: Type of content ('testimony' or 'miracle')
        content_id: ID of the content
    
    Returns list of all moderation actions taken on this content.
    """
    audit_logs = content_moderation_history(content_type=content_type, content_id=content_id)
    return [schemas.AuditLogSchema(**log.to_dict()) for log in audit_logs]


@router.post(
    "/{id}/flag_suspicious/",
    auth=jwt_auth,
    response={200: schemas.AuditLogSchema, 400: DetailOut},
)
@require_permission("flag_log_suspicious")
def flag_suspicious_audit_log_api(request, id: int):
    """
    Flag an audit log entry as suspicious.
    """
    audit_log = flag_suspicious_log(id)
    return audit_log


@router.post(
    "/{id}/unflag_suspicious/",
    auth=jwt_auth,
    response={200: schemas.AuditLogSchema, 400: DetailOut},
)
@require_permission("unflag_log_suspicious")
def unflag_suspicious_audit_log_api(request, id: int):
    """
    Unflag an audit log entry as suspicious.
    """
    audit_log = unflag_suspicious_log(id)
    return audit_log


@router.get(
    "/{id}/",
    auth=jwt_auth,
    response={200: schemas.AuditLogSchema, 400: DetailOut},
)
@require_permission("view_auditlog")
def get_audit_log(request, id: int):
    """
    Retrieve details of a specific audit log entry by its ID.
    """
    audit_log = audit_log_details(id)
    return schemas.AuditLogSchema(**audit_log.to_dict())