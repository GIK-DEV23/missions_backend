from datetime import timedelta
from typing import Optional

from django.db.models import Q, Count
from django.utils import timezone

from authentication import permissions_list
from base.utils.exceptions import CustomValidationError, NotFoundError
from users.filters import UserFilter, RoleFilter
from users.models import User, Role
from users.schemas import TimeFilter


def _get_time_filter_start(time_filter: TimeFilter):
    now = timezone.now()
    if time_filter == TimeFilter.LIFETIME:
        return None
    elif time_filter == TimeFilter.THIS_YEAR:
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == TimeFilter.LAST_YEAR:
        last_year = now.year - 1
        return now.replace(year=last_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_filter == TimeFilter.LAST_6_MONTHS:
        return now - timedelta(days=180)
    elif time_filter == TimeFilter.LAST_3_MONTHS:
        return now - timedelta(days=90)
    elif time_filter == TimeFilter.LAST_MONTH:
        return now - timedelta(days=30)
    return None


def _get_time_filter_end(time_filter: TimeFilter):
    if time_filter == TimeFilter.LAST_YEAR:
        now = timezone.now()
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def get_user_stats(user: User, time_filter: TimeFilter = TimeFilter.LIFETIME) -> dict:
    from souls.models import Soul, ProgressUpdate
    from souls.constants import ContactOutcome

    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    checks_in_this_week = ProgressUpdate.objects.filter(
        author=user,
        update_date__gte=week_start.date()
    ).count()

    time_start = _get_time_filter_start(time_filter)
    time_end = _get_time_filter_end(time_filter)

    user_souls = Soul.objects.filter(user=user, deleted_at__isnull=True)

    if time_start:
        user_souls = user_souls.filter(date_added__gte=time_start.date())
    if time_end:
        user_souls = user_souls.filter(date_added__lt=time_end.date())

    souls_won = user_souls.filter(contact_outcome=ContactOutcome.BORN_AGAIN).count()

    in_follow_up = user_souls.exclude(contact_outcome=ContactOutcome.BORN_AGAIN).count()

    # missionsCount definition (canonical):
    #   GIK missions where user has a registration AND >= 1 attended day
    #   + all personal missions (active + archived, never gated on souls)
    #
    # Rationale: participation/commitment stat, not outcome. A personal mission
    # created yesterday is real commitment; excluding empty missions would make
    # the count go DOWN as the user works. Archived = completed/ended, not erased.
    # Upcoming GIK registrations excluded: registration is intent, not participation.
    # days_of_attendance being non-empty is the attendance signal already in the schema.
    #
    # WARNING: the missions list screen must use the same logic or profile vs list
    # will show different numbers (guaranteed bug report).
    from missions.models import MissionJIAParticipant
    from personal_missions.models import PersonalMission

    gik_missions_count = MissionJIAParticipant.objects.filter(
        user=user,
        days_of_attendance__len__gt=0,
    ).values('mission').distinct().count()

    personal_missions_qs = PersonalMission.objects.filter(owner=user)
    if time_start:
        personal_missions_qs = personal_missions_qs.filter(created_at__gte=time_start)
    if time_end:
        personal_missions_qs = personal_missions_qs.filter(created_at__lt=time_end)
    personal_missions_count = personal_missions_qs.count()

    missions_count = gik_missions_count + personal_missions_count

    all_user_souls = Soul.objects.filter(user=user, deleted_at__isnull=True)
    souls_with_data_count = all_user_souls.count()
    souls_without_consent_count = all_user_souls.filter(consent_given=False).count()

    return {
        'checks_in_this_week': checks_in_this_week,
        'souls_won': souls_won,
        'in_follow_up': in_follow_up,
        'missions_count': missions_count,
        'souls_with_data_count': souls_with_data_count,
        'souls_without_consent_count': souls_without_consent_count,
    }


def role_details(role_id: int) -> Optional[Role]:
    """Get role details by ID"""
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        raise NotFoundError("Role with the given ID does not exist")


def user_details(user_id: Optional[int] = None, email: Optional[str] = None) -> Optional[User]:
    """Get user details by ID or email"""

    try:
        if user_id is not None:
            return User.objects.get(id=user_id)
        elif email is not None:
            return User.objects.get(email=email.lower())
        else:
            raise CustomValidationError("Either user_id or email must be provided")
    except User.DoesNotExist:
        raise NotFoundError("User with the given identifier does not exist")


def users_list(filters: dict = None):
    """Get list of users with optional filters"""
    if filters is None:
        filters = {}
    queryset = User.objects.all().order_by('id')
    search = filters.pop('search', None)
    if search:
        queryset = queryset.filter(
            (Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))
        )
    user_filter = UserFilter(filters, queryset=queryset)
    return user_filter.qs


def roles_list(filters: dict = None):
    """Get list of roles with optional filters"""
    queryset = Role.objects.all().order_by('id')
    if filters:
        roles_filter = RoleFilter(filters, queryset=queryset)
        return roles_filter.qs
    return queryset


def list_permissions(user_type: Optional[str] = None) -> list[str]:
    """Get list of permissions for a given user type"""
    role_map = {
        'missioner': permissions_list.MISSIONER_PERMISSIONS,
        'admin': permissions_list.ADMIN_PERMISSIONS,
        'exec': permissions_list.EXEC_PERMISSIONS,
        'staff': permissions_list.STAFF_PERMISSIONS,
    }
    if not user_type:
        return list(permissions_list.ALL_PERMISSIONS)
    return list(role_map.get(user_type.lower(), []))
