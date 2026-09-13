"""
Authentication utility functions.
"""
from typing import Dict, Optional, Tuple

from django.conf import settings

from authentication.backends import get_backend
from users.models import User, AuthProvider, UserAuthProvider, Role
from users.services import get_or_create_template_role


def get_auth_for_user(user: User) -> Dict:
    """
    Get authentication data for a user.

    This creates JWT tokens for the authenticated user.

    Args:
        user: The user to create authentication for

    Returns:
        Dictionary with authentication tokens and user data
    """
    # Get JWT backend
    jwt_backend = get_backend('jwt')
    if not jwt_backend:
        raise ValueError("JWT backend not available")

    # Generate token
    token_data = jwt_backend.generate_token(user)

    # Get user's primary auth provider if any
    primary_provider = user.get_primary_auth_provider()
    provider_name = primary_provider.provider.name if primary_provider else 'local'

    # Basic user data to return
    user_data = {
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'display_name': user.get_display_name(),
        'auth_provider': provider_name,
        'roles': list(user.roles.values_list('name', flat=True)),
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'phone_number': user.phone_number,
        'bio': user.bio,
        'church': user.church,
    }

    # Include profile photo URL if available
    if user.profile_photo:
        user_data['profile_photo'] = user.profile_photo.url

    # Return combined data
    return {
        **token_data,
        'user': user_data
    }


def create_auth_token(user: User) -> str:
    """
    Create an authentication token for a user.

    Args:
        user: The user to create a token for

    Returns:
        JWT token string
    """
    jwt_backend = get_backend('jwt')
    if not jwt_backend:
        raise ValueError("JWT backend not available")

    token_data = jwt_backend.generate_token(user)
    return token_data.get('access_token')


def authenticate_social_user(
    provider_name: str,
    provider_user_id: str,
    email: str,
    provider_data: Dict = None
) -> Tuple[User, bool]:
    """
    Authenticate or create a user via a social provider.

    This will either:
    1. Find an existing user with this social provider
    2. Find a user with the same email and link the social provider
    3. Create a new user with this social provider

    Args:
        provider_name: Name of the authentication provider
        provider_user_id: User ID from the provider
        email: User's email from the provider
        provider_data: Additional user data from the provider

    Returns:
        Tuple of (user, created) where created is True if a new user was created
    """
    # Check if this provider exists
    provider, _ = AuthProvider.objects.get_or_create(
        name=provider_name,
        defaults={
            "display_name": provider_name.capitalize(),
            "backend_class": f"authentication.backends.{provider_name}.{provider_name.capitalize()}AuthBackend",
            "config": {},
            "is_active": True,
            "allow_registration": True,
        },
    )

    if not provider.is_active:
        raise ValueError(f"Auth provider '{provider_name}' exists but is inactive")

    # Check if user already exists with this provider
    user_auth = UserAuthProvider.objects.filter(
        provider=provider,
        provider_user_id=provider_user_id
    ).first()

    if user_auth:
        # User already exists with this provider
        user_auth.mark_as_used()
        return user_auth.user, False

    # Check if user exists with this email
    user = User.objects.filter(email=email).first()
    created = False

    # Extract name data from provider data
    first_name = None
    last_name = None

    if provider_data:
        if provider_name == 'google':
            first_name = provider_data.get('given_name')
            last_name = provider_data.get('family_name')
        elif provider_name == 'apple':
            first_name = provider_data.get('first_name')
            last_name = provider_data.get('last_name')

    if not user:
        # Create new user
        username = email.split('@')[0]
        base_username = username
        counter = 1

        # Ensure username is unique
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name or '',
            last_name=last_name or '',
        )
        created = True

    # Link provider to user
    UserAuthProvider.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
        provider_data=provider_data or {},
        is_primary=created  # Set as primary if this is a new user
    )

    # Ensure user has 'missioner' role
    missioner_role = get_or_create_template_role('missioner')
    if not user.roles.filter(id=missioner_role.pk).exists():
        user.roles.add(missioner_role)

    return user, created
