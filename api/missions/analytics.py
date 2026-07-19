"""
Analytics selectors for mission reporting.

Provides:
1. System-wide reports (all missions) — yearly, half-year, quarterly, monthly
2. Per-mission reports — daily breakdown and full duration summary
Both include age group breakdowns of souls won.
"""
from datetime import date, timedelta
from typing import Optional

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone

from missions.models import Mission
from souls.models import Soul
from users.constants import AgeGroupCategory


def _age_group_breakdown(queryset):
    """Return souls count by age group for a given queryset."""
    breakdown = (
        queryset
        .values('age_group')
        .annotate(count=Count('id'))
        .order_by('age_group')
    )
    # Ensure all age groups appear even if count is 0
    result = {choice.value: 0 for choice in AgeGroupCategory}
    for entry in breakdown:
        if entry['age_group'] in result:
            result[entry['age_group']] = entry['count']
    return [{"age_group": k, "count": v} for k, v in result.items()]


def _get_period_start(period: str) -> date:
    """Get the start date for a named period relative to today."""
    today = timezone.now().date()
    if period == "this_month":
        return today.replace(day=1)
    elif period == "last_3_months":
        return (today - timedelta(days=90)).replace(day=1)
    elif period == "last_6_months":
        return (today - timedelta(days=180)).replace(day=1)
    elif period == "last_8_months":
        return (today - timedelta(days=240)).replace(day=1)
    elif period == "this_year":
        return today.replace(month=1, day=1)
    else:
        return today.replace(month=1, day=1)


def system_wide_analytics(year: Optional[int] = None):
    """
    Generate system-wide analytics across all missions.

    Returns:
        - summary: totals for various time periods
        - monthly_breakdown: souls won per month with age groups
        - missions_summary: counts by status
        - age_group_totals: overall age group breakdown
    """
    today = timezone.now().date()
    target_year = year or today.year

    # All souls for the target year
    year_souls = Soul.objects.filter(date_added__year=target_year)

    # Period summaries
    periods = {
        "this_month": year_souls.filter(date_added__gte=_get_period_start("this_month")),
        "last_3_months": year_souls.filter(date_added__gte=_get_period_start("last_3_months")),
        "last_6_months": year_souls.filter(date_added__gte=_get_period_start("last_6_months")),
        "last_8_months": year_souls.filter(date_added__gte=_get_period_start("last_8_months")),
        "this_year": year_souls,
    }

    summary = {}
    for period_name, qs in periods.items():
        summary[period_name] = {
            "total_souls": qs.count(),
            "new_converts": qs.filter(status="new_convert").count(),
            "follow_ups": qs.filter(status="follow_up").count(),
            "age_group_breakdown": _age_group_breakdown(qs),
        }

    # Monthly breakdown for the year
    monthly_data = (
        year_souls
        .annotate(month=TruncMonth('date_added'))
        .values('month')
        .annotate(
            total=Count('id'),
            new_converts=Count('id', filter=Q(status="new_convert")),
            follow_ups=Count('id', filter=Q(status="follow_up")),
        )
        .order_by('month')
    )

    monthly_breakdown = []
    for entry in monthly_data:
        month_souls = year_souls.filter(date_added__month=entry['month'].month)
        monthly_breakdown.append({
            "month": entry['month'].strftime("%Y-%m"),
            "total": entry['total'],
            "new_converts": entry['new_converts'],
            "follow_ups": entry['follow_ups'],
            "age_group_breakdown": _age_group_breakdown(month_souls),
        })

    # Missions summary
    all_missions = Mission.objects.filter(is_archived=False)
    missions_summary = {
        "total": all_missions.count(),
        "active": all_missions.filter(status="active").count(),
        "completed": all_missions.filter(status="completed").count(),
        "planning": all_missions.filter(status="planning").count(),
        "on_hold": all_missions.filter(status="on_hold").count(),
    }

    return {
        "year": target_year,
        "summary": summary,
        "monthly_breakdown": monthly_breakdown,
        "missions_summary": missions_summary,
        "age_group_totals": _age_group_breakdown(year_souls),
    }


def per_mission_analytics(mission_id: int):
    """
    Generate analytics for a specific mission.

    Returns:
        - mission_info: basic mission details
        - totals: overall soul counts for the mission
        - daily_breakdown: souls won per day with age groups
        - age_group_breakdown: overall age distribution for this mission
        - status_breakdown: souls by status
    """
    from missions.selectors import mission_details

    mission = mission_details(mission_id)
    mission_souls = Soul.objects.filter(mission=mission)

    # Overall totals
    totals = {
        "total_souls": mission_souls.count(),
        "new_converts": mission_souls.filter(status="new_convert").count(),
        "follow_ups": mission_souls.filter(status="follow_up").count(),
        "active": mission_souls.filter(status="active").count(),
    }

    # Daily breakdown (by date_added)
    daily_data = (
        mission_souls
        .annotate(day=TruncDate('date_added'))
        .values('day')
        .annotate(
            total=Count('id'),
            new_converts=Count('id', filter=Q(status="new_convert")),
            follow_ups=Count('id', filter=Q(status="follow_up")),
        )
        .order_by('day')
    )

    daily_breakdown = []
    for entry in daily_data:
        day_souls = mission_souls.filter(date_added=entry['day'])
        daily_breakdown.append({
            "date": entry['day'].strftime("%Y-%m-%d"),
            "total": entry['total'],
            "new_converts": entry['new_converts'],
            "follow_ups": entry['follow_ups'],
            "age_group_breakdown": _age_group_breakdown(day_souls),
        })

    # Gender breakdown
    gender_data = (
        mission_souls
        .values('gender')
        .annotate(count=Count('id'))
        .order_by('gender')
    )
    gender_breakdown = [{"gender": e['gender'], "count": e['count']} for e in gender_data]

    # Mission info
    mission_info = {
        "id": mission.id,
        "title": mission.title,
        "status": mission.status,
        "start_date": mission.start_date.strftime("%Y-%m-%d"),
        "end_date": mission.end_date.strftime("%Y-%m-%d"),
        "location": mission.location.name if mission.location else None,
        "category": mission.category.name if mission.category else None,
        "duration_days": (mission.end_date - mission.start_date).days + 1,
    }

    return {
        "mission": mission_info,
        "totals": totals,
        "daily_breakdown": daily_breakdown,
        "age_group_breakdown": _age_group_breakdown(mission_souls),
        "gender_breakdown": gender_breakdown,
    }
