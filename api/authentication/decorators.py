from functools import wraps
from django.http import JsonResponse

from authentication.permissions import has_role_type
from base.utils.exceptions import CustomValidationError, ForbiddenError


def require_permission(permission_tag, restricted_roles=None, restriction_handler=None):
    """
    Decorator to check permissions based on user role.
    Missioners automatically get access only to their own resources.

    Args:
        permission_tag: The permission required (e.g., "users:read")
        restricted_roles: The roles that have restrictions (e.g., ['missioner'])
        restriction_handler: The logic to handle restrictions for certain roles
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            # Authentication check
            if user is None:
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided."},
                    status=401
                )
            if not user.is_active:
                return JsonResponse({"detail": "Your account is disabled."}, status=403)

            # Gather user roles and permissions
            user_roles = user.roles.all()
            user_permissions = set()
            for role in user_roles:
                if role.permissions:
                    user_permissions.update(role.permissions)

            has_permission = permission_tag in user_permissions

            if user.is_superuser or has_role_type('superuser', roles=user_roles) or has_role_type('admin', roles=user_roles):
                return func(request, *args, **kwargs)

            if not has_permission:
                return JsonResponse({"detail": "Permission denied"}, status=403)

            if not restricted_roles:
                return func(request, *args, **kwargs)
            if restricted_roles and restriction_handler:
                role_names = [role.name.lower() for role in user_roles]
                restricted_lower = [r.lower() for r in restricted_roles]
                # Apply restriction only if ALL user roles are restricted
                if all(role_name in restricted_lower for role_name in role_names):
                    try:
                        restriction_handler(user, kwargs)
                    except (CustomValidationError, ForbiddenError) as e:
                        message = getattr(e, "message", None) or str(e)
                        return JsonResponse({"detail": message}, status=403)
                    except Exception as e:
                        return JsonResponse({"detail": f"Restriction error: {e}"}, status=400)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator