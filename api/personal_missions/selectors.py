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


def list_sessions(user, mission_id: int) -> List[PersonalMissionSession]:
    """
    List all sessions for a personal mission.
    
    Verifies the user owns the mission before returning sessions.
    """
    mission = get_personal_mission(user, mission_id)
    return mission.sessions.order_by('-date', '-created_at')
