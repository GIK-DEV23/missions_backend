from django.http import JsonResponse
from ninja import Router, Query, Form

from authentication import schemas as auth_schemas
from authentication.permissions import jwt_auth
from base.api import paginate_response
from base.schemas import DetailOut
from base.utils.exceptions import NotFoundError
from moderation import schemas as moderation_schemas
from moderation import selectors as moderation_selectors
from moderation import services as moderation_services
from users import selectors, services, schemas
from authentication.decorators import require_permission
from users.services import missioner_restriction_handler

router = Router(
    tags=["users"],
)


@router.get(
    "/me/",
    response={200: schemas.UserProfileOut},
    auth=jwt_auth
)
def get_own_profile_api(request):
    """Self-serve: view the caller's own full profile."""
    return schemas.UserProfileOut(**request.user.to_dict(request))


@router.get(
    "/me/stats/",
    response={200: schemas.MeStatsOut},
    auth=jwt_auth
)
def get_own_stats_api(request, params: schemas.MeStatsQuery = Query(...)):
    stats = selectors.get_user_stats(request.user, params.time_filter)
    return schemas.MeStatsOut(**stats)


@router.patch(
    "/me/",
    response={200: schemas.UserProfileOut, 400: DetailOut},
    auth=jwt_auth
)
def update_own_profile_api(request, profile_in: schemas.UserProfileUpdate):
    """Self-serve: update the caller's own profile. Never touches other users."""
    user = services.update_own_profile(request.user, profile_in.dict(exclude_unset=True))
    return 200, schemas.UserProfileOut(**user.to_dict(request))


@router.get(
    "/",
    response={200: list[auth_schemas.UserData], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_users")
def users_list_api(request, params: schemas.UserFilterSchema = Query(...)):
    users = selectors.users_list(filters=params.dict())
    response = paginate_response(
        queryset=users,
        request=request,
        schema=auth_schemas.UserData,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/create/",
    response={201: auth_schemas.UserData, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("add_user")
def create_user_api(request, user_in: schemas.UserCreate = Form(...)):
    profile_photo = request.FILES.get("profile_photo")
    user = services.create_user(
        profile_photo=profile_photo,
        **user_in.dict(exclude=["profile_photo"])
    )
    return 201, auth_schemas.UserData(**user.to_dict(request))


@router.post(
    "/activate/{user_id}/",
    response={200: auth_schemas.UserData, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("activate_user")
def activate_user_api(request, user_id: int):
    user = services.activate_user(user_id=user_id)
    return auth_schemas.UserData(**user.to_dict(request))


@router.post(
    "/deactivate/{user_id}/",
    response={200: auth_schemas.UserData, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("deactivate_user")
def deactivate_user_api(request, user_id: int):
    user = services.deactivate_user(user_id=user_id)
    return auth_schemas.UserData(**user.to_dict(request))


# ROLES AND PERMISSIONS


@router.get(
    "/roles/",
    response={200: list[schemas.RoleSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_roles")
def list_roles_api(request, params: schemas.RoleQuery = Query(...)):
    roles = selectors.roles_list(filters=params.dict())
    response = paginate_response(
        queryset=roles,
        request=request,
        schema=schemas.RoleSchema,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/permissions/",
    response={200: list[str], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_permissions")
def list_permissions_api(request, params: schemas.PermissionQuery = Query(...)):
    permissions = selectors.list_permissions(**params.dict())
    return permissions


@router.post(
    "/roles/create/",
    response={200: schemas.RoleOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("add_role")
def create_role_api(request, role_in: schemas.RoleCreate):
    role = services.create_role(
        name=role_in.name,
        permissions=role_in.permissions,
        description=role_in.description or ''
    )
    return schemas.RoleOut(**role.to_dict())


@router.get(
    "/check-email/",
    response={200: schemas.EmailExistsOut}
)
def check_email_exists_api(request, email: str = Query(...)):
    """
    Check if an email address is already registered.
    
    This endpoint is public (no auth required) to allow checking
    during the signup flow before credentials are submitted.
    """
    exists = services.check_email_exists(email)
    return schemas.EmailExistsOut(exists=exists)


# Registration defaults routes
@router.get(
    "/registration-defaults/",
    response={200: schemas.RegistrationDefaultsOut},
    auth=jwt_auth,
)
def get_registration_defaults_api(request):
    """Get the user's saved registration defaults for pre-filling mission sign-up forms."""
    return 200, schemas.RegistrationDefaultsOut(**selectors.get_registration_defaults(request.user))


@router.put(
    "/registration-defaults/",
    response={200: schemas.RegistrationDefaultsOut, 400: DetailOut},
    auth=jwt_auth,
)
def update_registration_defaults_api(request, defaults_in: schemas.RegistrationDefaultsUpdate):
    """Save/update the user's registration defaults for pre-filling mission sign-up forms."""
    user = services.update_registration_defaults(request.user, defaults_in.dict(exclude_unset=True))
    return 200, schemas.RegistrationDefaultsOut(**selectors.get_registration_defaults(user))


# Dynamic routes with path parameters - must be after static routes
@router.get(
    "/detail/{user_id}/",
    response={200: auth_schemas.UserData, 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "view_user",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_restriction_handler
)
def get_user_api(request, user_id: int):
    user = selectors.user_details(user_id=user_id)
    return auth_schemas.UserData(**user.to_dict(request))


@router.get(
    "/roles/{role_id}/",
    auth=jwt_auth,
    response={200: schemas.RoleOut, 400: DetailOut},
)
@require_permission("view_role")
def get_role_api(request, role_id: int):
    role = selectors.role_details(role_id=role_id)
    return schemas.RoleOut(**role.to_dict())


@router.delete(
    "/me/",
    response={200: DetailOut, 400: DetailOut, 403: DetailOut},
    auth=jwt_auth
)
@require_permission("request_own_deletion")
def delete_own_account_api(request):
    """
    Request erasure of the caller's own account.

    This starts a 30-day grace period rather than erasing immediately: the
    clients' own DeletionStatus union models `deletion_requested` and
    `in_grace_period`, and an irreversible delete on first tap has no undo for
    a mistaken or hijacked request. Cancel with POST /users/me/cancel-deletion/.

    Refused while the account is under legal hold.
    """
    record = moderation_services.request_deletion(request.user)
    return 200, DetailOut(detail=(
        "Account deletion requested. Your data will be erased after {}. "
        "You can cancel until then.".format(
            record.grace_period_ends_at.date().isoformat()
            if record.grace_period_ends_at else "the grace period ends"
        )
    ))


@router.get(
    "/me/deletion/",
    response={200: moderation_schemas.DeletionInfoOut, 404: DetailOut},
    auth=jwt_auth
)
def get_own_deletion_api(request):
    """Self-serve: where the caller's own erasure request stands."""
    record = moderation_selectors.get_user_deletion(request.user.pk)
    if record is None:
        raise NotFoundError("No deletion request exists for this account.")
    return 200, moderation_schemas.DeletionInfoOut(**record.to_dict(request))


@router.post(
    "/me/cancel-deletion/",
    response={200: moderation_schemas.DeletionInfoOut, 400: DetailOut},
    auth=jwt_auth
)
def cancel_own_deletion_api(request, body: moderation_schemas.CancelDeletionIn):
    """Self-serve: call off a pending erasure inside the grace period."""
    record = moderation_services.cancel_deletion(
        actor=request.user, user_id=request.user.pk, reason=body.reason
    )
    return 200, moderation_schemas.DeletionInfoOut(**record.to_dict(request))


# ─── Admin: erasure oversight (BR-1) ──────────────────────────────────────────

@router.get(
    "/deletion-status/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_user_deletion")
def users_deletion_status_api(request, params: moderation_schemas.DeletionStatusQuery = Query(...)):
    """Accounts with their erasure state. `deletion: null` means never requested."""
    users = moderation_selectors.list_users_with_deletion_status(
        filters=params.dict(exclude={"page", "page_size"})
    )
    response = moderation_selectors.paginate_users_with_deletion(
        queryset=users, page=params.page, page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/{user_id}/legal-hold/",
    response={200: moderation_schemas.UserWithDeletionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("set_legal_hold")
def set_legal_hold_api(request, user_id: int, body: moderation_schemas.LegalHoldIn):
    """Block erasure of this account until the hold is lifted."""
    record = moderation_services.set_legal_hold(
        admin=request.user, user_id=user_id, reason=body.reason
    )
    return 200, moderation_schemas.UserWithDeletionOut(
        **moderation_selectors.serialize_user_with_deletion(record.user, request)
    )


@router.delete(
    "/{user_id}/legal-hold/",
    response={200: moderation_schemas.UserWithDeletionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("remove_legal_hold")
def remove_legal_hold_api(request, user_id: int):
    """Lift a hold. Never erases the account as a side effect."""
    record = moderation_services.remove_legal_hold(admin=request.user, user_id=user_id)
    return 200, moderation_schemas.UserWithDeletionOut(
        **moderation_selectors.serialize_user_with_deletion(record.user, request)
    )


@router.post(
    "/{user_id}/cancel-deletion/",
    response={200: moderation_schemas.UserWithDeletionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("cancel_user_deletion")
def cancel_user_deletion_api(request, user_id: int, body: moderation_schemas.CancelDeletionIn):
    """Admin: call off a user's pending erasure."""
    record = moderation_services.cancel_deletion(
        actor=request.user, user_id=user_id, reason=body.reason
    )
    return 200, moderation_schemas.UserWithDeletionOut(
        **moderation_selectors.serialize_user_with_deletion(record.user, request)
    )
