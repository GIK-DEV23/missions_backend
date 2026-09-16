from datetime import date
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from personal_missions.constants import PersonalMissionType
from personal_missions.models import PersonalMission, PersonalMissionPeriod, PersonalMissionSession
from personal_missions.rhythm import get_period
from personal_missions.selectors import get_personal_mission

logger = logging.getLogger(__name__)


def _validate_what_happened(type_value, what_happened):
    if what_happened and type_value != PersonalMissionType.ONE_TIME:
        raise CustomValidationError("what_happened is only valid for one_time personal missions")


def create_personal_mission(owner, data: dict) -> PersonalMission:
    _validate_what_happened(data.get("type"), data.get("what_happened"))
    # Idempotent by (owner, client_id): if the same client creates this record
    # twice (e.g. retry after a network drop mid-response), return the existing
    # row rather than creating a duplicate.
    client_id = data.get("client_id")
    if client_id is not None:
        existing = PersonalMission.objects.filter(owner=owner, client_id=client_id).first()
        if existing is not None:
            return existing
    try:
        personal_mission = PersonalMission(owner=owner, **data)
        personal_mission.full_clean()
        personal_mission.save()
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError("Error creating personal mission: {}".format(e))
    return personal_mission


def update_personal_mission(user, personal_mission_id: int, data: dict) -> PersonalMission:
    personal_mission = get_personal_mission(user, personal_mission_id)
    new_type = data.get("type", personal_mission.type)
    new_what_happened = data.get("what_happened", personal_mission.what_happened)
    _validate_what_happened(new_type, new_what_happened)
    try:
        # `data` comes from `.dict(exclude_unset=True)` — every key here was
        # deliberately provided by the caller, including explicit nulls.
        for key, value in data.items():
            setattr(personal_mission, key, value)
        personal_mission.full_clean()
        personal_mission.save()
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError("Error updating personal mission: {}".format(e))
    return personal_mission


def archive_personal_mission(user, personal_mission_id: int) -> PersonalMission:
    personal_mission = get_personal_mission(user, personal_mission_id)
    personal_mission.archived_at = timezone.now()
    personal_mission.is_archived = True
    personal_mission.save(update_fields=["archived_at", "is_archived", "updated_at"])
    return personal_mission




@transaction.atomic
def mark_period_met(mission: PersonalMission, activity_date: date) -> None:
    """
    Mark the rhythm period containing activity_date as met.
    
    This function is idempotent and race-safe:
    - Uses get_or_create with unique constraint for concurrent sync safety
    - Does nothing if rhythm is 'none' or mission is archived
    - Does nothing if activity_date is outside mission date range
    
    Args:
        mission: PersonalMission instance
        activity_date: Date of the activity that triggers the mark
    """
    # Skip if no rhythm tracking or mission is archived
    if mission.rhythm == "none" or mission.archived_at:
        return
    
    # Calculate which period this activity falls into
    result = get_period(mission, activity_date)
    if result is None:
        logger.debug(
            "mark_period_met: activity_date %s outside valid range for mission %s",
            activity_date, mission.id
        )
        return
    
    period_index, period_start, period_end = result
    
    # get_or_create is atomic and idempotent with the unique constraint
    # If two sync workers race, one wins and the other gets the existing row
    _, created = PersonalMissionPeriod.objects.get_or_create(
        mission=mission,
        period_index=period_index,
        defaults={
            "period_start": period_start,
            "period_end": period_end,
            "met_at": timezone.now(),
        },
    )
    
    if created:
        logger.info(
            "mark_period_met: marked period %d as met for mission %s (date: %s)",
            period_index, mission.id, activity_date
        )


def create_session(user, mission_id: int, data: dict) -> PersonalMissionSession:
    """
    Log an explicit session for a personal mission.
    
    This allows users to record "I did my mission today" even when no new
    souls were added and no check-ins were logged.
    
    Args:
        user: The requesting user (must own the mission)
        mission_id: ID of the personal mission
        data: Session data (date, notes, souls_count, duration_minutes)
        
    Returns:
        The created PersonalMissionSession
    """
    mission = get_personal_mission(user, mission_id)
    
    try:
        with transaction.atomic():
            session = PersonalMissionSession(
                mission=mission,
                date=data.get("date", timezone.localdate()),
                notes=data.get("notes"),
                souls_count=data.get("souls_count", 0),
                duration_minutes=data.get("duration_minutes"),
            )
            session.full_clean()
            session.save()
            
            # Mark the rhythm period as met
            mark_period_met(mission, session.date)
            
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(f"Error creating session: {e}")
    
    return session
