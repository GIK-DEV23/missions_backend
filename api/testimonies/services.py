"""
Services for testimonies and miracles - create/update/delete business logic
"""
from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError

from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from base.utils.helpers import resolve_fk_by_client_id
from testimonies.constants import ReviewStatus
from testimonies.models import Testimony, Miracle, Highlight, TestimonyPhoto, MiraclePhoto, HighlightPhoto
from testimonies.selectors import testimony_details, miracle_details, highlight_details
from users.selectors import user_details
from souls.models import Soul
from souls.selectors import get_soul
from souls.services import user_has_soul_access
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


def approve_highlight(highlight_id: int) -> Highlight:
    highlight = highlight_details(highlight_id)
    highlight.review_status = ReviewStatus.APPROVED
    highlight.rejection_reason = None
    highlight.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return highlight


def reject_highlight(highlight_id: int, reason: str) -> Highlight:
    highlight = highlight_details(highlight_id)
    highlight.review_status = ReviewStatus.REJECTED
    highlight.rejection_reason = reason
    highlight.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    return highlight


def create_highlight(data: dict) -> Highlight:
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
        highlight = Highlight(**data)
        if photo:
            highlight.photo = photo
        highlight.full_clean()
        highlight.save()
        return highlight
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def update_highlight(highlight_id: int, update_dict: dict) -> Highlight:
    try:
        highlight = highlight_details(highlight_id)
        soul_id = update_dict.get('soul_id')
        user_id = update_dict.get('user_id')
        mission_id = update_dict.get('mission_id')

        if soul_id is not None:
            highlight.soul = get_soul(soul_id)
        if user_id is not None:
            highlight.user = user_details(user_id)
        if mission_id is not None:
            highlight.mission = mission_details(mission_id)

        photo = update_dict.get('photo')
        for key, value in update_dict.items():
            if key not in ('photo', 'soul_id', 'user_id', 'mission_id') and value is not None:
                setattr(highlight, key, value)
        if photo is not None:
            highlight.photo = photo
        highlight.full_clean()
        highlight.save()
        return highlight
    except Highlight.DoesNotExist:
        raise CustomValidationError('Highlight does not exist')
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def delete_highlight(highlight_id: int) -> Highlight:
    highlight = highlight_details(highlight_id)
    try:
        highlight.delete()
        return highlight
    except Exception as e:
        raise CustomValidationError(str(e))


def miracle_and_testimony_handler(user, kwargs):
    """Ownership restriction shared by testimony/miracle/highlight update endpoints."""
    testimony_in = kwargs.get('testimony_in')
    miracle_in = kwargs.get('miracle_in')
    highlight_in = kwargs.get('highlight_in')
    soul_id = (
        (testimony_in.soul_id if testimony_in else None)
        or (miracle_in.soul_id if miracle_in else None)
        or (highlight_in.soul_id if highlight_in else None)
        or kwargs.get('soul_id')
    )

    if not soul_id:
        return None

    soul = get_soul(soul_id)

    if not user_has_soul_access(user, soul):
        raise CustomValidationError("You can only edit miracles/testimonies/highlights for souls assigned to you.")
    return None

def bulk_create_testimony_photos(testimony_id: int, images_data: List[Dict[str, Any]]) -> List[TestimonyPhoto]:
    testimony = testimony_details(testimony_id)
    photos = []
    try:
        for data in images_data:
            photo = TestimonyPhoto(
                testimony=testimony,
                image=data['image'],
                title=data.get('title', ''),
                description=data.get('description', ''),
            )
            photo.full_clean()
            photos.append(photo)
        TestimonyPhoto.objects.bulk_create(photos)
        return photos
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def bulk_create_miracle_photos(miracle_id: int, images_data: List[Dict[str, Any]]) -> List[MiraclePhoto]:
    miracle = miracle_details(miracle_id)
    photos = []
    try:
        for data in images_data:
            photo = MiraclePhoto(
                miracle=miracle,
                image=data['image'],
                title=data.get('title', ''),
                description=data.get('description', ''),
            )
            photo.full_clean()
            photos.append(photo)
        MiraclePhoto.objects.bulk_create(photos)
        return photos
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def bulk_create_highlight_photos(highlight_id: int, images_data: List[Dict[str, Any]]) -> List[HighlightPhoto]:
    highlight = highlight_details(highlight_id)
    photos = []
    try:
        for data in images_data:
            photo = HighlightPhoto(
                highlight=highlight,
                image=data['image'],
                title=data.get('title', ''),
                description=data.get('description', ''),
            )
            photo.full_clean()
            photos.append(photo)
        HighlightPhoto.objects.bulk_create(photos)
        return photos
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))


def _check_soul_owned_by(user, soul) -> None:
    if not soul or not user_has_soul_access(user, soul):
        raise CustomValidationError("You can only manage photos for souls assigned to you.")


def testimony_photo_restriction_handler(user, kwargs):
    testimony_id = kwargs.get('testimony_id')
    if not testimony_id:
        return None
    testimony = testimony_details(testimony_id)
    _check_soul_owned_by(user, testimony.soul)
    return None


def miracle_photo_restriction_handler(user, kwargs):
    miracle_id = kwargs.get('miracle_id')
    if not miracle_id:
        return None
    miracle = miracle_details(miracle_id)
    _check_soul_owned_by(user, miracle.soul)
    return None


def highlight_photo_restriction_handler(user, kwargs):
    highlight_id = kwargs.get('highlight_id')
    if not highlight_id:
        return None
    highlight = highlight_details(highlight_id)
    _check_soul_owned_by(user, highlight.soul)
    return None
