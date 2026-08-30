from typing import Optional, List

from django.core.exceptions import ValidationError

from authentication.permissions import has_role_type
from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from authentication import permissions_list
from users.models import User, Role
from users.schemas import UserType
from users.selectors import role_details, user_details


def create_user(
    email: str,
    password: str = None,
    first_name: str = '',
    last_name: str = '',
    preferred_username: str = None,
    profile_photo: Optional[str] = None,
    user_type: Optional[UserType] = None,
    role_id: Optional[int] = None,
    permissions: Optional[list] = None,
    role_name: Optional[str] = None
) -> User:
    """
    Create a new user with the given details.

    Args:
        email: User's email address
        password: User's password (optional)
        first_name: User's first name (optional)
        last_name: User's last name (optional)
        preferred_username: User's preferred username (optional)
        profile_photo: User's profile photo (optional)
        user_type: Type of the user to assign a template role (e.g., 'admin', 'missioner') (optional)
        role_id: ID of an existing role to assign to the user (optional)
        permissions: List of permissions to create a new role with (optional)
        role_name: Name of the new role to create if permissions are provided (optional)
    Returns:
        The created User instance
    Raises:
        ValueError: If email is not provided
        CustomValidationError: If neither permissions nor role_id is provided
    """
    try:
        email = email.lower()
        with transaction.atomic():
            user = User(
                email=email,
                username=email,
                first_name=first_name,
                last_name=last_name,
                preferred_username=preferred_username,
                profile_photo=profile_photo
            )

            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.full_clean()
            user.save()

            if user_type:
                template_role = get_or_create_template_role(user_type.value)
                user.roles.add(template_role)
                return user

            if not permissions and not role_id:
                raise CustomValidationError("Either permissions or role_id must be provided")
            if role_id:
                role = role_details(role_id=role_id)
            else:
                if not role_name:
                    raise CustomValidationError("role_name must be provided when creating a role with permissions")
                role = create_role(name=role_name, permissions=permissions or [])
            if role:
                user.roles.add(role)
            return user
    except IntegrityError:
        raise CustomValidationError("There exists a user with the provided details")
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("An unexpected error occurred: {}".format(e))

def register_missioner(
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    confirm_password: str,
    preferred_username: Optional[str] = None,
    profile_photo: Optional[str] = None
):
    if password != confirm_password:
        raise CustomValidationError("Passwords did not match")

    if preferred_username is None:
        preferred_username = first_name

    user = create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
        preferred_username=preferred_username,
        password=password,
        profile_photo=profile_photo,
        user_type=UserType.MISSIONER
    )

    return user


from django.db import transaction, IntegrityError


def create_role(name: str, permissions: list, description: str = '') -> Role:
    if not name:
        raise ValueError("Role name is required")
    if not permissions:
        raise ValueError("At least one permission is required to create a role")

    with transaction.atomic():
        role, created = Role.objects.get_or_create(name=name, defaults={
            "permissions": permissions,
            "description": description,
        })
        if not created:
            # Update if permissions or description changed
            updated = False
            if role.permissions != permissions:
                role.permissions = permissions
                updated = True
            if description and role.description != description:
                role.description = description
                updated = True
            if updated:
                role.save()
        return role


def get_or_create_template_role(user_type: str) -> Role:
    """
    Get or create a template role based on user type.

    Args:
        user_type: Type of the user (e.g., 'admin', 'missioner')
    Returns:
        The Role instance corresponding to the user type
    Raises:
        ValueError: If user_type is not recognized
    """
    role_map = {
        'missioner': permissions_list.MISSIONER_PERMISSIONS,
        'admin': permissions_list.ADMIN_PERMISSIONS,
        'exec': permissions_list.EXEC_PERMISSIONS,
        'staff': permissions_list.STAFF_PERMISSIONS,
        'superuser': permissions_list.SUPERUSER_PERMISSIONS
    }
    if user_type not in role_map:
        raise ValueError(f"Unknown user type: {user_type}")
    role_name = f"{user_type}_template"
    permissions = list(role_map[user_type])
    role = create_role(name=role_name, permissions=permissions, description=f"Template role for {user_type}s")
    return role


def deactivate_user(user_id: int) -> User:
    """
    Deactivate a user account.

    Args:
        user_id: The id of the User instance to deactivate
    """
    user = user_details(user_id=user_id)
    user.is_active = False
    user.save()
    return user


def activate_user(user_id: int) -> User:
    """
    Activate a user account.

    Args:
        user_id: The id of the User instance to activate
    """
    user = user_details(user_id=user_id)
    user.is_active = True
    user.save()
    return user


def update_own_profile(user: User, data: dict) -> User:
    """Self-serve profile update — only touches fields a user may set on themselves.

    `data` is expected from `.dict(exclude_unset=True)` — every key present
    was deliberately provided, including explicit nulls, so they're all
    applied (no `is not None` guard; see personal_missions ticket for why
    that guard is wrong when the caller already filtered to explicit keys).
    """
    try:
        for key, value in data.items():
            setattr(user, key, value)
        user.full_clean()
        user.save()
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    except Exception as e:
        raise CustomValidationError("Error updating profile: {}".format(e))
    return user


def missioner_restriction_handler(user, kwargs):
    """
    Restriction handler for missioner role.
    Ensures missioners can only access their own resources.
    """
    print("user in restriction handler:", user)
    requested_user_id = kwargs.get('user_id')

    # Missioners can only access their own data
    if requested_user_id and requested_user_id != user.id:
        raise CustomValidationError("You can only access your own details.")
