"""
Services for testimonies and miracles - create/update/delete business logic
"""
from typing import Optional
from django.core.exceptions import ValidationError

from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from base.utils.helpers import resolve_fk_by_client_id
from testimonies.constants import ReviewStatus
from testimonies.models import Testimony, Miracle
from testimonies.selectors import testimony_details, miracle_details
from users.selectors import user_details
from souls.models import Soul
from souls.selectors import get_soul
from missions.selectors import mission_details


def create_testimony(data: dict) -> Testimony:
    try:
        data = resolve_fk_by_client_id(data, "soul", Soul)
        soul_id = data.get('soul_id')
        user_id = data.get('user_id')
        mission_id = data.get('mission_id')

        if soul_id is not None:
            soul = get_soul(soul_id)
            data['soul'] = soul
        if user_id is not None:
            user = user_details(user_id)
            data['user'] = user
        if mission_id is not None:
            mission = mission_details(mission_id)
            data['mission'] = mission

        photo = data.pop('photo', None)
        testimony = Testimony(**data)
        if photo:
            testimony.photo = photo
        testimony.full_clean()
        testimony.save()
        return testimony
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def update_testimony(testimony_id: int, update_dict: dict) -> Testimony:
    try:
        testimony = testimony_details(testimony_id)
        soul_id = update_dict.get('soul_id')
        user_id = update_dict.get('user_id')
        mission_id = update_dict.get('mission_id')

        if soul_id is not None:
            testimony.soul = get_soul(soul_id)
        if user_id is not None:
            testimony.user = user_details(user_id)
        if mission_id is not None:
            testimony.mission = mission_details(mission_id)

        photo = update_dict.get('photo')
        for key, value in update_dict.items():
            if key not in ('photo', 'soul_id', 'user_id', 'mission_id') and value is not None:
                setattr(testimony, key, value)
        if photo is not None:
            testimony.photo = photo
        testimony.full_clean()
        testimony.save()
        return testimony
    except Testimony.DoesNotExist:
        raise CustomValidationError('Testimony does not exist')
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def delete_testimony(testimony_id: int) -> Testimony:
    testimony = testimony_details(testimony_id)
    try:
        testimony.delete()
        return testimony
    except Exception as e:
        raise CustomValidationError(str(e))


def approve_testimony(testimony_id: int) -> Testimony:
    testimony = testimony_details(testimony_id)
    testimony.review_status = ReviewStatus.APPROVED
    testimony.rejection_reason = None
    testimony.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return testimony


def reject_testimony(testimony_id: int, reason: str) -> Testimony:
    testimony = testimony_details(testimony_id)
    testimony.review_status = ReviewStatus.REJECTED
    testimony.rejection_reason = reason
    testimony.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return testimony


# Miracles

def create_miracle(data: dict) -> Miracle:
    try:
        data = resolve_fk_by_client_id(data, "soul", Soul)
        soul_id = data.get('soul_id')
        user_id = data.get('user_id')
        mission_id = data.get('mission_id')

        if soul_id is not None:
            data['soul'] = get_soul(soul_id)
        if user_id is not None:
            data['user'] = user_details(user_id)
        if mission_id is not None:
            data['mission'] = mission_details(mission_id)

        photo = data.pop('photo', None)
        miracle = Miracle(**data)
        if photo:
            miracle.photo = photo
        miracle.full_clean()
        miracle.save()
        return miracle
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def update_miracle(miracle_id: int, update_dict: dict) -> Miracle:
    try:
        miracle = miracle_details(miracle_id)
        soul_id = update_dict.get('soul_id')
        user_id = update_dict.get('user_id')
        mission_id = update_dict.get('mission_id')

        if soul_id is not None:
            miracle.soul = get_soul(soul_id)
        if user_id is not None:
            miracle.user = user_details(user_id)
        if mission_id is not None:
            miracle.mission = mission_details(mission_id)

        photo = update_dict.get('photo')
        for key, value in update_dict.items():
            if key not in ('photo', 'soul_id', 'user_id', 'mission_id') and value is not None:
                setattr(miracle, key, value)
        if photo is not None:
            miracle.photo = photo
        miracle.full_clean()
        miracle.save()
        return miracle
    except Miracle.DoesNotExist:
        raise CustomValidationError('Miracle does not exist')
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def delete_miracle(miracle_id: int) -> Miracle:
    miracle = miracle_details(miracle_id)
    try:
        miracle.delete()
        return miracle
    except Exception as e:
        raise CustomValidationError(str(e))


def approve_miracle(miracle_id: int) -> Miracle:
    miracle = miracle_details(miracle_id)
    miracle.review_status = ReviewStatus.APPROVED
    miracle.rejection_reason = None
    miracle.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return miracle


def reject_miracle(miracle_id: int, reason: str) -> Miracle:
    miracle = miracle_details(miracle_id)
    miracle.review_status = ReviewStatus.REJECTED
    miracle.rejection_reason = reason
    miracle.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return miracle


def miracle_and_testimony_handler(user, kwargs):
    testimony_in = kwargs.get('testimony_in')
    miracle_in = kwargs.get('miracle_in')
    soul_id = (
        (testimony_in.soul_id if testimony_in else None)
        or (miracle_in.soul_id if miracle_in else None)
        or kwargs.get('soul_id')
    )

    if not soul_id:
        return None

    soul = get_soul(soul_id)

    if not soul.user or soul.user.pk != user.pk:
        raise CustomValidationError("You can only edit miracles/testimonies for souls assigned to you.")
    return None