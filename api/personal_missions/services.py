from django.core.exceptions import ValidationError
from django.utils import timezone

from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from personal_missions.constants import PersonalMissionType
from personal_missions.models import PersonalMission
from personal_missions.selectors import get_personal_mission


def _validate_what_happened(type_value, what_happened):
    if what_happened and type_value != PersonalMissionType.ONE_TIME:
        raise CustomValidationError("what_happened is only valid for one_time personal missions")


def create_personal_mission(owner, data: dict) -> PersonalMission:
    _validate_what_happened(data.get("type"), data.get("what_happened"))
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
