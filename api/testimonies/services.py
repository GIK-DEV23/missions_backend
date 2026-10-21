"""
Services for testimonies and miracles - create/update/delete business logic
"""
from typing import Optional
from django.core.exceptions import ValidationError

from base.utils.exceptions import CustomValidationError, ForbiddenError, handle_cleaning_error
from base.utils.helpers import resolve_fk_by_client_id
from testimonies.constants import ReviewStatus
from testimonies.models import Testimony, Miracle
from testimonies.selectors import testimony_details, miracle_details
from users.selectors import user_details
from souls.models import Soul
from souls.selectors import get_soul
from missions.selectors import mission_details
from audit_logs.services import log_moderation_action
from audit_logs.constants import ActionType, ContentType


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


def approve_testimony(testimony_id: int, moderator=None) -> Testimony:
    testimony = testimony_details(testimony_id)
    previous_status = testimony.review_status
    testimony.review_status = ReviewStatus.APPROVED
    testimony.rejection_reason = None
    testimony.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.APPROVE,
            content_type=ContentType.TESTIMONY,
            content_id=testimony.id,
            content_title=testimony.title,
            previous_status=previous_status,
            new_status=ReviewStatus.APPROVED
        )
    
    return testimony


def feature_testimony(testimony_id: int, duration_days: Optional[int] = None, feature_order: int = 0, moderator=None) -> Testimony:
    """
    Feature a testimony on the home screen.
    
    Args:
        testimony_id: ID of the testimony to feature
        duration_days: Number of days to feature (None = indefinite)
        feature_order: Display order (lower = higher priority)
        moderator: User performing the action
    """
    from django.utils import timezone
    from datetime import timedelta
    
    testimony = testimony_details(testimony_id)
    
    # Must be approved to be featured
    if testimony.review_status != ReviewStatus.APPROVED:
        raise CustomValidationError("Only approved testimonies can be featured.")
    
    testimony.is_selected = True
    testimony.feature_order = feature_order
    
    if duration_days is not None and duration_days > 0:
        testimony.featured_until = timezone.now() + timedelta(days=duration_days)
    else:
        testimony.featured_until = None  # Indefinite
    
    testimony.save(update_fields=["is_selected", "featured_until", "feature_order", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.FEATURE,
            content_type=ContentType.TESTIMONY,
            content_id=testimony.id,
            content_title=testimony.title,
            details=f"Featured for {duration_days} days" if duration_days else "Featured indefinitely"
        )
    
    return testimony


def unfeature_testimony(testimony_id: int, moderator=None) -> Testimony:
    """Remove a testimony from the featured highlights."""
    testimony = testimony_details(testimony_id)
    
    testimony.is_selected = False
    testimony.featured_until = None
    testimony.feature_order = 0
    testimony.save(update_fields=["is_selected", "featured_until", "feature_order", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.UNFEATURE,
            content_type=ContentType.TESTIMONY,
            content_id=testimony.id,
            content_title=testimony.title
        )
    
    return testimony


def reorder_featured_testimonies(testimony_ids: list, moderator=None) -> list:
    """
    Reorder featured testimonies by setting their feature_order based on position in the list.
    
    Args:
        testimony_ids: List of testimony IDs in desired display order
        moderator: User performing the action
    """
    updated = []
    for order, testimony_id in enumerate(testimony_ids):
        testimony = testimony_details(testimony_id)
        if testimony.is_selected:
            testimony.feature_order = order
            testimony.save(update_fields=["feature_order", "updated_at"])
            updated.append(testimony)
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.REORDER,
            content_type=ContentType.TESTIMONY,
            content_id=0,  # Not specific to one testimony
            content_title="Featured testimonies",
            details=f"Reordered {len(updated)} testimonies"
        )
    
    return updated


def reject_testimony(testimony_id: int, reason: str, moderator=None) -> Testimony:
    testimony = testimony_details(testimony_id)
    previous_status = testimony.review_status
    testimony.review_status = ReviewStatus.REJECTED
    testimony.rejection_reason = reason
    testimony.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.REJECT,
            content_type=ContentType.TESTIMONY,
            content_id=testimony.id,
            content_title=testimony.title,
            previous_status=previous_status,
            new_status=ReviewStatus.REJECTED,
            rejection_reason=reason
        )
    
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


def approve_miracle(miracle_id: int, moderator=None) -> Miracle:
    miracle = miracle_details(miracle_id)
    previous_status = miracle.review_status
    miracle.review_status = ReviewStatus.APPROVED
    miracle.rejection_reason = None
    miracle.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.APPROVE,
            content_type=ContentType.MIRACLE,
            content_id=miracle.id,
            content_title=miracle.title,
            previous_status=previous_status,
            new_status=ReviewStatus.APPROVED
        )
    
    return miracle


def reject_miracle(miracle_id: int, reason: str, moderator=None) -> Miracle:
    miracle = miracle_details(miracle_id)
    previous_status = miracle.review_status
    miracle.review_status = ReviewStatus.REJECTED
    miracle.rejection_reason = reason
    miracle.save(update_fields=["review_status", "rejection_reason", "updated_at"])
    
    # Log moderation action
    if moderator:
        log_moderation_action(
            user=moderator,
            action_type=ActionType.REJECT,
            content_type=ContentType.MIRACLE,
            content_id=miracle.id,
            content_title=miracle.title,
            previous_status=previous_status,
            new_status=ReviewStatus.REJECTED,
            rejection_reason=reason
        )
    
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
        raise ForbiddenError("You can only edit miracles/testimonies for souls assigned to you.")
    return None


def check_anonymous_rate_limit(device_token_hash: str) -> bool:
    import hashlib
    from datetime import timedelta
    from django.conf import settings
    from django.utils import timezone
    from testimonies.models import AnonymousSubmissionToken

    rate_limit = getattr(settings, 'ANON_SUBMISSION_RATE_LIMIT', 5)
    window_hours = getattr(settings, 'ANON_SUBMISSION_RATE_WINDOW_HOURS', 24)
    window_start_threshold = timezone.now() - timedelta(hours=window_hours)

    token, created = AnonymousSubmissionToken.objects.get_or_create(
        device_token_hash=device_token_hash
    )

    if not created and token.window_start < window_start_threshold:
        token.window_start = timezone.now()
        token.submission_count = 0
        token.save(update_fields=['window_start', 'submission_count'])

    return token.submission_count < rate_limit


def record_anonymous_submission(device_token_hash: str):
    from django.utils import timezone
    from testimonies.models import AnonymousSubmissionToken

    AnonymousSubmissionToken.objects.filter(device_token_hash=device_token_hash).update(
        submission_count=models.F('submission_count') + 1,
        last_submission_at=timezone.now()
    )


def hash_device_token(device_token: str) -> str:
    import hashlib
    return hashlib.sha256(device_token.encode()).hexdigest()


def create_anonymous_testimony(data: dict) -> Testimony:
    from django.db import models

    device_token = data.pop('device_token')
    device_token_hash = hash_device_token(device_token)

    if not check_anonymous_rate_limit(device_token_hash):
        raise CustomValidationError("Rate limit exceeded. Please try again later.")

    mission_id = data.get('mission_id')
    if mission_id is not None:
        data['mission'] = mission_details(mission_id)

    try:
        testimony = Testimony(**data)
        testimony.full_clean()
        testimony.save()
        record_anonymous_submission(device_token_hash)
        return testimony
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))