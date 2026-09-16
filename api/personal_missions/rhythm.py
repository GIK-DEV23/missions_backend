"""
Rhythm period calculation for personal missions.

Computes which period index a given activity date falls into, based on the
mission's start_date, rhythm type, and rhythm_day settings.

Period 0 starts at the "anchor date" — the first occurrence of rhythm_day
on or after start_date for weekly/fortnightly, or the 1st of the month
containing start_date for monthly.
"""
from datetime import date, timedelta
from typing import Optional, Tuple

from personal_missions.constants import PersonalMissionRhythm

# Days per period for weekly/fortnightly rhythms
DAYS_PER_PERIOD = {
    PersonalMissionRhythm.WEEKLY: 7,
    PersonalMissionRhythm.FORTNIGHTLY: 14,
}


def _add_months(d: date, months: int) -> date:
    """Add months to a date, clamping day to valid range for target month."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    # Clamp day to max days in target month
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return date(year, month, day)


def get_anchor_date(mission) -> date:
    """
    Compute the anchor date (first day of period 0) for a mission.
    
    For weekly/fortnightly: First occurrence of rhythm_day on or after start_date.
    For monthly: The 1st of the month containing start_date.
    
    Args:
        mission: PersonalMission instance with start_date, rhythm, rhythm_day
        
    Returns:
        The anchor date for period calculations
    """
    if mission.rhythm == PersonalMissionRhythm.MONTHLY:
        # Period 0 = the month containing start_date
        return mission.start_date.replace(day=1)
    
    if mission.rhythm in DAYS_PER_PERIOD:
        # First occurrence of rhythm_day on or after start_date
        # rhythm_day: 0=Monday, 6=Sunday (matches Python's weekday())
        rhythm_day = mission.rhythm_day if mission.rhythm_day is not None else 0
        days_ahead = (rhythm_day - mission.start_date.weekday()) % 7
        return mission.start_date + timedelta(days=days_ahead)
    
    # For rhythm=none, anchor at start_date (though we won't track)
    return mission.start_date


def get_period(
    mission,
    activity_date: date,
) -> Optional[Tuple[int, date, date]]:
    """
    Calculate which period an activity date falls into.
    
    Args:
        mission: PersonalMission instance
        activity_date: The date of the activity
        
    Returns:
        Tuple of (period_index, period_start, period_end) or None if:
        - rhythm is 'none' (no tracking)
        - activity_date is before mission start_date
        - activity_date is after mission end_date (if set)
    """
    # No rhythm = no tracking
    if mission.rhythm == PersonalMissionRhythm.NONE:
        return None
    
    # Activity before mission started
    if activity_date < mission.start_date:
        return None
    
    # Activity after mission ended
    if mission.end_date and activity_date > mission.end_date:
        return None
    
    anchor = get_anchor_date(mission)
    
    if mission.rhythm == PersonalMissionRhythm.MONTHLY:
        # Calculate months between anchor and activity_date
        idx = (activity_date.year - anchor.year) * 12 + (activity_date.month - anchor.month)
        
        # Period start is 1st of the month
        period_start = _add_months(anchor, idx)
        
        # Period end is last day of the month
        next_month = _add_months(period_start, 1)
        period_end = next_month - timedelta(days=1)
        
        return idx, period_start, period_end
    
    # Weekly or fortnightly
    days_per = DAYS_PER_PERIOD[mission.rhythm]
    
    # Handle activity before anchor (between start_date and first rhythm_day)
    if activity_date < anchor:
        # This activity is in "period 0" even though it's before anchor
        # because it's after start_date
        idx = 0
        period_start = mission.start_date
        period_end = anchor - timedelta(days=1)
        return idx, period_start, period_end
    
    # Normal case: activity is on or after anchor
    idx = (activity_date - anchor).days // days_per
    period_start = anchor + timedelta(days=idx * days_per)
    period_end = period_start + timedelta(days=days_per - 1)
    
    return idx, period_start, period_end


def get_period_bounds(mission, anchor: date, period_index: int) -> Tuple[date, date]:
    """
    Calculate the start and end dates for a given period index.
    
    Used by the selector to generate the display timeline.
    
    Args:
        mission: PersonalMission instance
        anchor: Pre-computed anchor date from get_anchor_date()
        period_index: 0-based period index
        
    Returns:
        Tuple of (period_start, period_end)
    """
    if mission.rhythm == PersonalMissionRhythm.MONTHLY:
        period_start = _add_months(anchor, period_index)
        next_month = _add_months(period_start, 1)
        period_end = next_month - timedelta(days=1)
        return period_start, period_end
    
    days_per = DAYS_PER_PERIOD.get(mission.rhythm, 7)
    period_start = anchor + timedelta(days=period_index * days_per)
    period_end = period_start + timedelta(days=days_per - 1)
    
    return period_start, period_end


def get_current_period_index(mission, today: date) -> Optional[int]:
    """
    Get the current period index for a mission as of today.
    
    Args:
        mission: PersonalMission instance
        today: Current date
        
    Returns:
        Current period index, or None if rhythm is 'none' or mission hasn't started
    """
    result = get_period(mission, today)
    if result is None:
        return None
    return result[0]
