"""
1. Get soul by id
2. List souls with filters
3. Get progress updates by id
4. List progress updates with filters
"""
from datetime import timedelta
from enum import Enum
from typing import Optional, Dict, Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from authentication.permissions import has_role_type
from base.utils.exceptions import NotFoundError
from base.utils.helpers import apply_sorting
from souls.constants import FollowUpHealth
from souls.filters import SoulFilter
from souls.models import Soul, ProgressUpdate


def compute_follow_up_health(soul: Soul) -> Optional[str]:
    if soul.do_not_contact:
        return None

    reference_date = soul.last_contacted_at or soul.date_added
    if reference_date is None:
        return None

    if hasattr(reference_date, 'date'):
        reference_date = reference_date.date()

    days_since = (timezone.now().date() - reference_date).days

    due_days = getattr(settings, 'SOUL_FOLLOWUP_DUE_DAYS', 7)
    overdue_days = getattr(settings, 'SOUL_FOLLOWUP_OVERDUE_DAYS', 14)
    dormant_days = getattr(settings, 'SOUL_FOLLOWUP_DORMANT_DAYS', 60)

    if days_since >= dormant_days:
        return FollowUpHealth.DORMANT
    elif days_since >= overdue_days:
        return FollowUpHealth.OVERDUE
    elif days_since >= due_days:
        return FollowUpHealth.DUE
    return FollowUpHealth.HEALTHY


def filter_by_follow_up_health(queryset, health: FollowUpHealth):
    today = timezone.now().date()
    due_days = getattr(settings, 'SOUL_FOLLOWUP_DUE_DAYS', 7)
    overdue_days = getattr(settings, 'SOUL_FOLLOWUP_OVERDUE_DAYS', 14)
    dormant_days = getattr(settings, 'SOUL_FOLLOWUP_DORMANT_DAYS', 60)

    due_threshold = today - timedelta(days=due_days)
    overdue_threshold = today - timedelta(days=overdue_days)
    dormant_threshold = today - timedelta(days=dormant_days)

    base_filter = Q(do_not_contact=False)

    if health == FollowUpHealth.HEALTHY:
        return queryset.filter(
            base_filter,
            Q(last_contacted_at__date__gt=due_threshold) | 
            Q(last_contacted_at__isnull=True, date_added__gt=due_threshold)
        )
    elif health == FollowUpHealth.DUE:
        return queryset.filter(
            base_filter,
            (
                Q(last_contacted_at__date__lte=due_threshold, last_contacted_at__date__gt=overdue_threshold) |
                Q(last_contacted_at__isnull=True, date_added__lte=due_threshold, date_added__gt=overdue_threshold)
            )
        )
    elif health == FollowUpHealth.OVERDUE:
        return queryset.filter(
            base_filter,
            (
                Q(last_contacted_at__date__lte=overdue_threshold, last_contacted_at__date__gt=dormant_threshold) |
                Q(last_contacted_at__isnull=True, date_added__lte=overdue_threshold, date_added__gt=dormant_threshold)
            )
        )
    elif health == FollowUpHealth.DORMANT:
        return queryset.filter(
            base_filter,
            Q(last_contacted_at__date__lte=dormant_threshold) |
            Q(last_contacted_at__isnull=True, date_added__lte=dormant_threshold)
        )
    return queryset


def get_soul(soul_id: int):
    """Retrieve a soul by its ID. Excludes souls merged away via /merge/."""

    try:
        return Soul.objects.get(id=soul_id, deleted_at__isnull=True)
    except Soul.DoesNotExist:
        raise NotFoundError("Soul with ID {} does not exist".format(soul_id))


def get_soul_by_client_id(client_id):
    """Retrieve a soul by its client_id. Excludes souls merged away via /merge/."""

    try:
        return Soul.objects.get(client_id=client_id, deleted_at__isnull=True)
    except Soul.DoesNotExist:
        raise NotFoundError("Soul with client_id {} does not exist".format(client_id))


def list_souls(
    user,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: Optional[str] = None,
    is_desc: bool = True,
    follow_up_health: Optional[FollowUpHealth] = None
):
    """List souls with optional filters."""
    if sort_by is None:
        sort_by = 'uploaded_at'
    if isinstance(sort_by, Enum):
        sort_by = sort_by.value
    qs = Soul.objects.filter(deleted_at__isnull=True)
    is_special_user = has_role_type("admin", user=user) or has_role_type("superadmin", user=user) or has_role_type("staff", user=user) or has_role_type("executive", user=user)
    if not is_special_user:
        qs = qs.filter(user=user)
    qs = apply_sorting(
        qs,
        sort_by=sort_by,
        is_desc=is_desc,
        allowed_fields=['uploaded_at', 'first_name', 'phone_number', 'date_added']
    )
    if filters:
        qs = SoulFilter(filters, queryset=qs).qs
    if follow_up_health:
        qs = filter_by_follow_up_health(qs, follow_up_health)
    return qs


def souls_stats(user, filters: Optional[Dict[str, Any]] = None):
    """Get statistics about souls with optional filters."""
    from django.db.models.functions import TruncMonth
    from django.db.models import Count

    qs = Soul.objects.filter(deleted_at__isnull=True)
    if filters:
        qs = SoulFilter(filters, queryset=qs).qs
    total_souls = qs.count()
    personal_won_souls = qs.filter(user=user).count()

    # Monthly breakdown aggregated by date_added
    souls_by_month = (
        qs.annotate(month=TruncMonth('date_added'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    souls_by_month_list = [
        {"month": entry["month"].strftime("%Y-%m"), "count": entry["count"]}
        for entry in souls_by_month if entry["month"] is not None
    ]

    return {
        "total_souls": total_souls,
        "personal_won_souls": personal_won_souls,
        "souls_by_month": souls_by_month_list,
    }

def get_progress_update(id: int):
    """Retrieve a progress update by its ID."""
    try:
        return ProgressUpdate.objects.get(id=id)
    except ProgressUpdate.DoesNotExist:
        raise NotFoundError("ProgressUpdate with ID {} does not exist".format(id))


def get_soul_activity(soul_id: int):
    """Get all progress updates for a soul, ordered by most recent first."""
    soul = get_soul(soul_id)
    return soul.progress_updates.all().order_by('-update_date', '-created_at')


def list_progress_updates(
    soul_id: Optional[int] = None,
    is_desc: bool = True
):
    """List progress updates with optional soul filter."""
    qs = ProgressUpdate.objects.all()
    qs = apply_sorting(
        qs,
        sort_by='update_date',
        is_desc=is_desc,
        allowed_fields=['update_date']
    )
    if soul_id is not None:
        qs = qs.filter(soul=soul_id)
    return qs


def get_soul_assignment(assignment_id: int):
    from souls.models import SoulAssignment
    try:
        return SoulAssignment.objects.get(id=assignment_id)
    except SoulAssignment.DoesNotExist:
        raise NotFoundError("SoulAssignment with ID {} does not exist".format(assignment_id))


def list_soul_assignments(soul_id: int):
    from souls.models import SoulAssignment
    return SoulAssignment.objects.filter(soul_id=soul_id).order_by('-is_active', '-created_at')
