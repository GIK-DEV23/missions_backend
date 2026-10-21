from datetime import date
from typing import Any, Dict, List, Optional

from django.utils import timezone

from base.utils.exceptions import NotFoundError
from personal_missions.models import PersonalMission, PersonalMissionSession
from personal_missions.rhythm import get_anchor_date, get_period, get_period_bounds


# Number of periods to include in the rhythm timeline
RHYTHM_WINDOW = 21


def get_personal_mission(user, personal_mission_id: int) -> PersonalMission:
    try:
        return PersonalMission.objects.get(id=personal_mission_id, owner=user)
    except PersonalMission.DoesNotExist:
        raise NotFoundError("PersonalMission with ID {} does not exist".format(personal_mission_id))


def list_personal_missions(user):
    return PersonalMission.objects.filter(owner=user).order_by('-updated_at', '-created_at')


def list_personal_missions_with_rhythm(user, include_archived: bool = False) -> List[Dict[str, Any]]:
    """
    List personal missions with computed rhythm data.
    
    Uses prefetch_related to efficiently load met_periods in one query,
    then computes the rhythm timeline for each mission.
    
    Args:
        user: The owner of the missions
        include_archived: If False (default), excludes archived missions.
                         If True, returns all missions including archived.
    """
    queryset = (
        PersonalMission.objects
        .filter(owner=user)
        .prefetch_related("met_periods")
        .order_by('-updated_at', '-created_at')
    )
    
    if not include_archived:
        queryset = queryset.filter(archived_at__isnull=True)
    
    today = timezone.localdate()
    return [serialize_mission_with_rhythm(m, today) for m in queryset]


def list_archived_personal_missions_with_rhythm(user) -> List[Dict[str, Any]]:
    """
    List only archived personal missions with computed rhythm data.
    
    Used for lazy-loading archived missions in the UI accordion.
    """
    missions = (
        PersonalMission.objects
        .filter(owner=user, archived_at__isnull=False)
        .prefetch_related("met_periods")
        .order_by('-archived_at', '-updated_at')
    )
    
    today = timezone.localdate()
    return [serialize_mission_with_rhythm(m, today) for m in missions]


def serialize_mission_with_rhythm(
    mission: PersonalMission,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Serialize a personal mission with computed rhythm tracking data.
    
    Generates the last RHYTHM_WINDOW periods, marking each as met or missed
    based on the presence of PersonalMissionPeriod rows.
    
    Args:
        mission: PersonalMission instance (should have met_periods prefetched)
        today: Reference date for computing current period (defaults to today)
        
    Returns:
        Dict with mission fields + rhythm_periods, met_count, current_period_index
    """
    if today is None:
        today = timezone.localdate()
    
    # Start with base mission data
    data = mission.to_dict()
    
    # Handle missions with no rhythm tracking
    if mission.rhythm == "none":
        data.update({
            "rhythm_periods": [],
            "met_count": 0,
            "current_period_index": None,
        })
        return data
    
    # Compute current period index
    current_result = get_period(mission, today)
    if current_result is None:
        # Mission hasn't started yet or has ended
        data.update({
            "rhythm_periods": [],
            "met_count": 0,
            "current_period_index": None,
        })
        return data
    
    current_idx = current_result[0]
    anchor = get_anchor_date(mission)
    
    # Build a set of met period indices for O(1) lookup
    # (met_periods should be prefetched to avoid N+1)
    met_by_idx = {p.period_index: p for p in mission.met_periods.all()}
    
    # Generate the rhythm timeline for the last RHYTHM_WINDOW periods
    start_idx = max(0, current_idx - RHYTHM_WINDOW + 1)
    periods = []
    
    for idx in range(start_idx, current_idx + 1):
        period_start, period_end = get_period_bounds(mission, anchor, idx)
        met_period = met_by_idx.get(idx)
        
        periods.append({
            "index": idx,
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "met": met_period is not None,
            "met_at": met_period.met_at.isoformat() if met_period else None,
        })
    
    data.update({
        "rhythm_periods": periods,
        "met_count": sum(1 for p in periods if p["met"]),
        "current_period_index": current_idx,
    })
    
    return data


def personal_mission_details(personal_mission_id: int) -> PersonalMission:
    """Non-owner-scoped lookup for other apps linking to a personal mission by FK."""
    try:
        return PersonalMission.objects.get(id=personal_mission_id)
    except PersonalMission.DoesNotExist:
        raise NotFoundError("PersonalMission with ID {} does not exist".format(personal_mission_id))


# ─── Organisation-wide reads (BR-2) ───────────────────────────────────────────

def list_all_personal_missions(filters: Optional[Dict[str, Any]] = None):
    """Every user's personal missions, for admin oversight.

    The owner-scoped list at GET /personal-missions/ returns request.user's own
    records, so an admin page built on it shows the admin's own missions rather
    than the organisation's. This is the separate, permission-gated read that
    an admin surface needs; the owner-scoped route is left exactly as mobile
    depends on it.
    """
    filters = filters or {}
    queryset = (
        PersonalMission.objects
        .select_related("owner")
        .prefetch_related("met_periods")
    )

    owner_id = filters.get("user")
    if owner_id:
        queryset = queryset.filter(owner_id=owner_id)

    mission_type = filters.get("type")
    if mission_type:
        queryset = queryset.filter(type=mission_type)

    rhythm = filters.get("rhythm")
    if rhythm:
        queryset = queryset.filter(rhythm=rhythm)

    if not filters.get("include_archived"):
        queryset = queryset.filter(archived_at__isnull=True)

    return queryset.order_by("-updated_at", "-created_at")


def paginate_personal_missions_with_rhythm(queryset, page: int, page_size: int) -> Dict[str, Any]:
    """Paginate admin-scoped missions, computing each one's rhythm timeline.

    Hand-rolled rather than base.api.paginate_response because the rhythm
    fields are computed per row rather than living on the model, so a plain
    to_dict would omit them.
    """
    from django.core.paginator import Paginator

    from base.utils.exceptions import CustomValidationError

    paginator = Paginator(queryset, page_size)
    if page > paginator.num_pages:
        raise CustomValidationError("Invalid page number")
    current = paginator.get_page(page)
    today = timezone.localdate()
    return {
        "count": paginator.count,
        "page": current.number,
        "page_size": page_size,
        "last_page": paginator.num_pages,
        "data": [serialize_mission_with_rhythm(m, today) for m in current],
    }


def list_sessions(user, mission_id: int) -> List[PersonalMissionSession]:
    """
    List all sessions for a personal mission.
    
    Verifies the user owns the mission before returning sessions.
    """
    mission = get_personal_mission(user, mission_id)
    return mission.sessions.order_by('-date', '-created_at')
