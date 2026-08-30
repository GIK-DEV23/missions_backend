from django.http import JsonResponse
from ninja import Router, Query, Form

from authentication import schemas as auth_schemas
from authentication.permissions import jwt_auth
from base.api import paginate_response
from base.schemas import DetailOut
from users import selectors, services, schemas
from authentication.decorators import require_permission
from users.services import missioner_restriction_handler

router = Router(
    tags=["users"],
)
me_router = Router(tags=["me"])


@me_router.get(
    "/data-export/",
    response={200: dict},
    auth=jwt_auth
)
def data_export_api(request):
    """Kenya DPA: full export of the caller's own data across the system."""
    return 200, services.export_user_data(request.user)


@me_router.delete(
    "/",
    response={200: DetailOut},
    auth=jwt_auth
)
def request_account_deletion_api(request):
    """Kenya DPA: deletion request — deactivates the account immediately,
    data purge is a separate later process, not an immediate wipe."""
    services.request_account_deletion(request.user)
    return 200, {"detail": "Account deletion requested. Your account has been deactivated; data removal will follow."}


@router.get(
    "/me/",
    response={200: schemas.UserProfileOut},
    auth=jwt_auth
)
def get_own_profile_api(request):
    """Self-serve: view the caller's own full profile."""
    return schemas.UserProfileOut(**request.user.to_dict(request))


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
@require_permission("create_role")
def create_role_api(request, role_in: schemas.RoleCreate):
    role = services.create_role(
        name=role_in.name,
        permissions=role_in.permissions,
        description=role_in.description or ''
    )
    return schemas.RoleOut(**role.to_dict())


@router.get(
    "/{user_id}/",
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
