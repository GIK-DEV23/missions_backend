import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone

from authentication.models import PasswordResetToken
from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from users.models import User

RESET_TOKEN_TTL_MINUTES = 30


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _send_reset_email(user: User, raw_token: str) -> None:
    deep_link = "{}?token={}".format(settings.PASSWORD_RESET_DEEP_LINK_BASE, raw_token)
    send_mail(
        subject="Reset your GIK Missions password",
        message=(
            "Tap the link below to reset your password. This link expires "
            "in {} minutes and can only be used once.\n\n{}"
        ).format(RESET_TOKEN_TTL_MINUTES, deep_link),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def request_password_reset(email: str) -> None:
    """Always behaves identically whether or not the email exists — the
    caller (the API view) always returns success either way."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user:
        return
    raw_token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    _send_reset_email(user, raw_token)


def reset_password(token: str, new_password: str) -> None:
    token_hash = _hash_token(token)
    reset_token = PasswordResetToken.objects.filter(token_hash=token_hash, used_at__isnull=True).first()
    if not reset_token or not reset_token.is_valid:
        raise CustomValidationError("Invalid or expired token")

    user = reset_token.user
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))

    user.set_password(new_password)
    user.save(update_fields=["password"])

    now = timezone.now()
    reset_token.used_at = now
    reset_token.save(update_fields=["used_at"])

    # A successful reset retires every other outstanding link for this user.
    PasswordResetToken.objects.filter(
        user=user, used_at__isnull=True
    ).exclude(id=reset_token.id).update(used_at=now)
