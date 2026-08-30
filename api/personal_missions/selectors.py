from base.utils.exceptions import CustomValidationError
from personal_missions.models import PersonalMission


def get_personal_mission(user, personal_mission_id: int) -> PersonalMission:
    try:
        return PersonalMission.objects.get(id=personal_mission_id, owner=user)
    except PersonalMission.DoesNotExist:
        raise CustomValidationError("PersonalMission with ID {} does not exist".format(personal_mission_id))


def list_personal_missions(user):
    return PersonalMission.objects.filter(owner=user)


def personal_mission_details(personal_mission_id: int) -> PersonalMission:
    """Non-owner-scoped lookup for other apps linking to a personal mission by FK."""
    try:
        return PersonalMission.objects.get(id=personal_mission_id)
    except PersonalMission.DoesNotExist:
        raise CustomValidationError("PersonalMission with ID {} does not exist".format(personal_mission_id))
