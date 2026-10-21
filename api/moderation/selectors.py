"""Moderation reads."""

from datetime import timedelta
from typing import Any, Dict, Optional

from django.db.models import Avg, Count, F, QuerySet
from django.utils import timezone

from base.utils.exceptions import NotFoundError
from moderation.constants import (
    ReportableContentType,
    ReportStatus,
    TERMINAL_REPORT_STATUSES,
)
from moderation.models import ContentReport, UserDeletion

#: Characters of the reported body shown in the review queue.
PREVIEW_EXCERPT_CHARS = 280


def get_report(report_id: int) -> ContentReport:
    try:
        return ContentReport.objects.select_related("reporter", "reviewed_by").get(
            id=report_id
        )
    except ContentReport.DoesNotExist:
        raise NotFoundError("ContentReport with ID {} does not exist".format(report_id))


def list_reports(filters: Optional[Dict[str, Any]] = None) -> QuerySet[ContentReport]:
    """Filtered report queue, newest first.

    Unknown keys are ignored rather than dropped silently into the ORM, so a
    stale client filter cannot widen the result set.
    """
    filters = filters or {}
    queryset = ContentReport.objects.select_related("reporter", "reviewed_by")

    status = filters.get("status")
    if status:
        queryset = queryset.filter(status=status)

    content_type = filters.get("content_type")
    if content_type:
        queryset = queryset.filter(content_type=content_type)

    reason = filters.get("reason")
    if reason:
        queryset = queryset.filter(reason=reason)

    start_date = filters.get("start_date")
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)

    end_date = filters.get("end_date")
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)

    return queryset.order_by("-created_at")


def list_reports_by_reporter(reporter) -> QuerySet[ContentReport]:
    """A reporter's own reports, newest first.

    Separate from list_reports because that is the REVIEW queue: it is gated on
    `list_content_reports`, which an ordinary missioner does not hold, and it
    spans every reporter. Someone who filed a report still needs to see what
    happened to it, which is what the mobile "my reports" screen shows.
    """
    return (
        ContentReport.objects.filter(reporter=reporter)
        .select_related("reviewed_by")
        .order_by("-created_at")
    )


# ─── Content preview ──────────────────────────────────────────────────────────

def _submission_preview(model, content_id: int) -> Optional[Dict[str, Any]]:
    obj = model.objects.select_related("user").filter(id=content_id).first()
    if obj is None:
        return None
    return {
        "title": obj.title,
        "body_excerpt": (obj.content or "")[:PREVIEW_EXCERPT_CHARS],
        "author_name": obj.user.get_full_name() if obj.user else None,
        "author_id": obj.user_id,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "exists": True,
    }


def _soul_preview(content_id: int) -> Optional[Dict[str, Any]]:
    from souls.models import Soul

    soul = Soul.objects.select_related("user").filter(id=content_id).first()
    if soul is None:
        return None
    # A Soul has no body text, and its description is pastoral notes about a
    # third party, so it is deliberately not excerpted into the review queue.
    return {
        "title": soul.get_full_name(),
        "body_excerpt": None,
        "author_name": soul.user.get_full_name() if soul.user else None,
        "author_id": soul.user_id,
        "created_at": soul.created_at.isoformat() if soul.created_at else None,
        "exists": True,
    }


def _user_preview(content_id: int) -> Optional[Dict[str, Any]]:
    from users.models import User

    user = User.objects.filter(id=content_id).first()
    if user is None:
        return None
    return {
        "title": user.get_display_name(),
        "body_excerpt": user.bio or None,
        "author_name": user.get_full_name(),
        "author_id": user.pk,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "exists": True,
    }


def resolve_content_preview(content_type: str, content_id: int) -> Dict[str, Any]:
    """Look up the reported row for the review queue.

    Returns ``exists: False`` rather than raising when the target is gone: a
    report on content that was since deleted must still be reviewable and
    closable, otherwise the queue jams on rows nobody can action.
    """
    from testimonies.models import Miracle, Testimony

    if content_type == ReportableContentType.TESTIMONY:
        preview = _submission_preview(Testimony, content_id)
    elif content_type == ReportableContentType.MIRACLE:
        preview = _submission_preview(Miracle, content_id)
    elif content_type == ReportableContentType.SOUL:
        preview = _soul_preview(content_id)
    elif content_type == ReportableContentType.USER:
        preview = _user_preview(content_id)
    else:
        preview = None

    if preview is None:
        return {
            "title": None,
            "body_excerpt": None,
            "author_name": None,
            "author_id": None,
            "created_at": None,
            "exists": False,
        }
    return preview


def content_exists(content_type: str, content_id: int) -> bool:
    return bool(resolve_content_preview(content_type, content_id)["exists"])


# ─── Statistics ───────────────────────────────────────────────────────────────

def moderation_stats() -> Dict[str, Any]:
    """Counts for the dashboard's moderation header."""
    queryset = ContentReport.objects.all()
    week_ago = timezone.now() - timedelta(days=7)

    resolved = queryset.filter(
        status__in=list(TERMINAL_REPORT_STATUSES),
        reviewed_at__isnull=False,
    )

    # Average wall-clock hours from report to decision, over resolved reports
    # only — including open ones would make the figure fall as the queue grows.
    avg_delta = resolved.aggregate(
        avg=Avg(F("reviewed_at") - F("created_at"))
    )["avg"]
    avg_hours = round(avg_delta.total_seconds() / 3600, 2) if avg_delta else 0.0

    by_reason = (
        queryset.values("reason").annotate(count=Count("id")).order_by("-count")
    )
    by_content_type = (
        queryset.values("content_type").annotate(count=Count("id")).order_by("-count")
    )

    return {
        "total_reports": queryset.count(),
        "pending_reports": queryset.filter(
            status__in=[ReportStatus.PENDING, ReportStatus.UNDER_REVIEW]
        ).count(),
        "resolved_this_week": resolved.filter(reviewed_at__gte=week_ago).count(),
        "avg_resolution_time_hours": avg_hours,
        "reports_by_reason": [
            {"reason": row["reason"], "count": row["count"]} for row in by_reason
        ],
        "reports_by_content_type": [
            {"content_type": row["content_type"], "count": row["count"]}
            for row in by_content_type
        ],
    }


# ─── Account deletion ─────────────────────────────────────────────────────────

def get_user_deletion(user_id: int) -> Optional[UserDeletion]:
    return (
        UserDeletion.objects.select_related("legal_hold_by")
        .filter(user_id=user_id)
        .first()
    )


def list_users_with_deletion_status(filters: Optional[Dict[str, Any]] = None):
    """Users annotated with their erasure record, for the admin table.

    Without a `deletion_status` filter this is every user, because the
    dashboard's table doubles as the account list; `deletion: null` means the
    account never requested erasure.
    """
    from users.models import User

    filters = filters or {}
    queryset = User.objects.select_related("deletion", "deletion__legal_hold_by")

    deletion_status = filters.get("deletion_status")
    if deletion_status:
        queryset = queryset.filter(deletion__status=deletion_status)

    return queryset.order_by("-date_joined")


def due_for_erasure() -> QuerySet[UserDeletion]:
    """Deletion requests whose grace period has elapsed and are not held.

    Read by the scheduled erasure job; a legal hold keeps a row out of this
    set for as long as the hold stands.
    """
    from moderation.constants import DeletionStatus

    return UserDeletion.objects.filter(
        status__in=[DeletionStatus.DELETION_REQUESTED, DeletionStatus.IN_GRACE_PERIOD],
        grace_period_ends_at__lte=timezone.now(),
    ).select_related("user")


def serialize_user_with_deletion(user, request=None) -> Dict[str, Any]:
    """One row of the admin deletion table.

    `deletion` is None for an account that never requested erasure, which is
    what the dashboard's `DeletionInfo | null` expects.
    """
    record = getattr(user, "deletion", None)
    return {
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name or None,
        "last_name": user.last_name or None,
        "display_name": user.get_display_name(),
        "is_active": user.is_active,
        "deletion": (
            {
                "status": record.status,
                "requested_at": (
                    record.requested_at.isoformat() if record.requested_at else None
                ),
                "grace_period_ends_at": (
                    record.grace_period_ends_at.isoformat()
                    if record.grace_period_ends_at
                    else None
                ),
                "completed_at": (
                    record.completed_at.isoformat() if record.completed_at else None
                ),
                "legal_hold_reason": record.legal_hold_reason or None,
                "legal_hold_by": (
                    {
                        "id": record.legal_hold_by.pk,
                        "name": record.legal_hold_by.get_full_name(),
                    }
                    if record.legal_hold_by
                    else None
                ),
                "legal_hold_at": (
                    record.legal_hold_at.isoformat() if record.legal_hold_at else None
                ),
            }
            if record is not None
            else None
        ),
    }


def paginate_users_with_deletion(queryset, page: int, page_size: int) -> Dict[str, Any]:
    """Paginate the deletion table.

    Hand-rolled rather than using base.api.paginate_response because that
    helper serializes through each row's own ``to_dict``, and the deletion
    record lives on a related model rather than on User.
    """
    from django.core.paginator import Paginator

    from base.utils.exceptions import CustomValidationError

    paginator = Paginator(queryset, page_size)
    if page > paginator.num_pages:
        raise CustomValidationError("Invalid page number")
    current = paginator.get_page(page)
    return {
        "count": paginator.count,
        "page": current.number,
        "page_size": page_size,
        "last_page": paginator.num_pages,
        "data": [serialize_user_with_deletion(u) for u in current],
    }
