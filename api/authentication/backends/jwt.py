"""
JWT authentication backend implementation.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Dict, Optional, Tuple

import jwt
import pytz
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from authentication.backends.base import AuthBackend
from authentication.backends.registry import register_backend
from users.models import User


@register_backend
class JWTAuthBackend(AuthBackend):
    name = 'jwt'
    display_name = 'JWT Authentication'
    supports_registration = False
    requires_config = False

    DEFAULT_JWT_SECRET = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    DEFAULT_JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    DEFAULT_ACCESS_EXPIRATION = settings.NINJA_JWT.get(
        'ACCESS_TOKEN_LIFETIME', timedelta(minutes=45)
    )
    DEFAULT_REFRESH_EXPIRATION = settings.NINJA_JWT.get(
        'REFRESH_TOKEN_LIFETIME', timedelta(days=90)
    )

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.jwt_secret = self.config.get('secret_key', self.DEFAULT_JWT_SECRET)
        self.algorithm = self.config.get('algorithm', self.DEFAULT_JWT_ALGORITHM)
        self.access_expiration = self.DEFAULT_ACCESS_EXPIRATION
        self.refresh_expiration = self.DEFAULT_REFRESH_EXPIRATION

    def generate_token(self, user: User) -> Dict:
        return self.generate_token_pair(user)

    def generate_token_pair(self, user: User) -> Dict:
        now = timezone.now()
        access_expiry = now + self.access_expiration
        refresh_expiry = now + self.refresh_expiration

        access_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'is_superuser': user.is_superuser,
            'exp': access_expiry.timestamp(),
            'iat': now.timestamp(),
            'type': 'access',
        }
        roles = list(user.roles.values_list('name', flat=True))
        if roles:
            access_payload['roles'] = roles

        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.algorithm)

        refresh_payload = {
            'user_id': str(user.id),
            'exp': refresh_expiry.timestamp(),
            'iat': now.timestamp(),
            'type': 'refresh',
            'jti': secrets.token_hex(16),
        }
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.algorithm)

        self._store_refresh_token(user, refresh_token, refresh_expiry)

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(self.access_expiration.total_seconds()),
        }

    def _store_refresh_token(self, user: User, token: str, expires_at):
        from authentication.models import RefreshToken
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        RefreshToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )

    def validate_refresh_token(self, token: str) -> Tuple[bool, Optional[User], str]:
        from authentication.models import RefreshToken

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return False, None, "Refresh token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid refresh token: {str(e)}"

        if payload.get('type') != 'refresh':
            return False, None, "Token is not a refresh token"

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored_token = RefreshToken.objects.filter(token_hash=token_hash).first()

        if not stored_token:
            return False, None, "Refresh token not found"

        if stored_token.blacklisted_at:
            return False, None, "Refresh token has been revoked"

        if not stored_token.is_valid:
            return False, None, "Refresh token has expired"

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return False, None, "User not found"

        return True, user, ""

    def blacklist_refresh_token(self, token: str) -> bool:
        from authentication.models import RefreshToken
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored_token = RefreshToken.objects.filter(token_hash=token_hash).first()
        if stored_token:
            stored_token.blacklist()
            return True
        return False

    def rotate_refresh_token(self, old_token: str) -> Tuple[bool, Dict, str]:
        valid, user, error = self.validate_refresh_token(old_token)
        if not valid:
            return False, {}, error

        self.blacklist_refresh_token(old_token)
        new_tokens = self.generate_token_pair(user)
        return True, new_tokens, ""

    def authenticate(self, request: HttpRequest, **kwargs) -> Tuple[bool, Dict, Optional[str]]:
        token = kwargs.get('token') or self.extract_auth_token(request)

        if not token:
            return False, {}, "No JWT token provided"

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
            nairobi_tz = pytz.timezone("Africa/Nairobi")

            if 'exp' in payload:
                exp_dt = datetime.fromtimestamp(payload['exp'], tz=dt_timezone.utc).astimezone(nairobi_tz)
                now_nairobi = timezone.now().astimezone(nairobi_tz)
                if exp_dt < now_nairobi:
                    return False, {}, "Token has expired"

            user_data = {
                'provider_user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'is_superuser': payload.get('is_superuser', False),
                'roles': payload.get('roles', []),
            }

            return True, user_data, None

        except jwt.ExpiredSignatureError:
            return False, {}, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, {}, f"Invalid token: {str(e)}"

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
            return payload.get('user_id')
        except jwt.PyJWTError:
            return None

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
