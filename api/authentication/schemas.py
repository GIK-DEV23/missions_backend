"""
Authentication schemas for Django Ninja API.
"""
from typing import Dict, List, Optional, Any

from ninja import Schema
from pydantic import EmailStr, Field, model_validator


class LoginRequest(Schema):
    """Schema for login requests."""
    email: EmailStr
    password: str


class SocialAuthRequest(Schema):
    """Schema for social authentication requests."""
    provider: str
    code: Optional[str] = None
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None  # For Apple's initial auth with name data


class TokenData(Schema):
    """Schema for authentication tokens."""
    access_token: str
    token_type: str
    expires_in: int


class ManualRegisterRequest(Schema):
    """Schema for user manual registration."""
    email: EmailStr
    first_name: str
    last_name: str
    preferred_username: Optional[str] = None
    profile_photo: Optional[str] = None
    password: str
    confirm_password: str


class UserData(Schema):
    """Schema for user data returned in auth responses."""
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: str
    roles: List[str] = []
    is_superuser: bool = False
    is_staff: bool = False
    profile_photo: Optional[str] = None


class AuthResponse(Schema):
    """Schema for successful authentication responses."""
    access_token: str
    token_type: str
    expires_in: int
    user: UserData


class SocialAuthResponse(AuthResponse):
    """Schema for successful social authentication responses."""
    is_new_user: bool = False


class TokenVerificationResponse(Schema):
    """Schema for token verification responses."""
    valid: bool
    user: Optional[UserData] = None


class AuthProviderInfo(Schema):
    """Schema for auth provider information."""
    name: str
    display_name: str
    supports_registration: bool
    auth_url: Optional[str] = None
    priority: int


class AuthProviderListResponse(Schema):
    """Schema for listing available authentication providers."""
    providers: List[AuthProviderInfo]


class TokenRefreshIn(Schema):
    """Schema for token refresh requests."""
    access_token: str = Field(..., description="The refresh token to obtain a new access token.")


class RequestPasswordResetIn(Schema):
    email: EmailStr


class ResetPasswordIn(Schema):
    token: str
    new_password: str
