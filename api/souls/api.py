
from typing import List

from django.http import JsonResponse
from ninja import Router, Query, UploadedFile, File, Form

from base.schemas import DetailOut
from souls import selectors, services, schemas
from authentication.permissions import jwt_auth
from base.api import paginate_response
from souls.services import progress_update_handler, missioner_soul_operations_handler
from authentication.decorators import require_permission

router = Router(
    tags=["souls"],
)


@require_permission("list_souls")
@router.get(
    "/",
    response={200: List[schemas.SoulOut]},
    auth=jwt_auth
)
def souls_list_api(request, params: schemas.SoulsQuery = Query(...)):
    """API endpoint to list souls with optional filters and pagination."""
    souls = selectors.list_souls(
        user=request.user,
        filters=params.dict(),
        sort_by=params.sort_by,
        is_desc=params.is_desc
    )
    response = paginate_response(
        queryset=souls,
        request=request,
        schema=schemas.SoulOut,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@require_permission("souls_stats")
@router.get(
    "/stats/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
def souls_stats_api(request, params: schemas.SoulsQuery = Query(...)):
    """API endpoint to list souls with optional filters and pagination."""
    souls_count = selectors.souls_stats(
        user=request.user,
        filters=params.dict()
    )
    return 200, souls_count


@require_permission("create_soul")
@router.post(
    "create/",
    response={201: schemas.SoulOut},
    auth=jwt_auth
)
def create_soul_api(request, soul_in: schemas.SoulCreate):
    """API endpoint to create a new soul."""
    soul = services.create_soul(soul_in.dict())
    return 201, schemas.SoulOut(**soul.to_dict(request))


@require_permission("upload_souls")
@router.post(
    "/upload_souls/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
def upload_souls_api(
    request,
    mission_id: int = Form(...),
    location_id: int = Form(...),
    file: UploadedFile = File(...)
):
    """
    Upload an Excel/CSV file of souls.
    Example fields:
        - missioner_email
        - first_name
        - last_name
        - phone_number
        - gender
        - age_group
        - description
        - date_added
    """
    result = services.upload_souls(user=request.user, file=file, mission_id=mission_id, location_id=location_id)
    return JsonResponse(result)


@require_permission("update_soul")
@router.patch(
    "/{soul_id}/update/",
    response={200: schemas.SoulOut},
    auth=jwt_auth
)
def update_soul_api(request, soul_id: int, soul_in: schemas.SoulUpdate):
    """API endpoint to update an existing soul."""
    soul = services.update_soul(user=request.user, soul_id=soul_id, data=soul_in.dict())
    return schemas.SoulOut(**soul.to_dict(request))


@require_permission("delete_soul")
@router.delete(
    "/{soul_id}/delete/",
    response={200: schemas.SoulOut},
    auth=jwt_auth
)
def delete_soul_api(request, soul_id: int):
    """API endpoint to delete a soul by ID."""
    soul = services.delete_soul(user=request.user, soul_id=soul_id)
    return schemas.SoulOut(**soul.to_dict(request))


@require_permission("merge_soul")
@router.post(
    "/{soul_id}/merge/",
    response={200: schemas.SoulOut, 400: DetailOut},
    auth=jwt_auth
)
def merge_soul_api(request, soul_id: int, merge_in: schemas.SoulMergeIn):
    """Merge a duplicate soul into another, reassigning its history."""
    survivor = services.merge_souls(user=request.user, soul_id=soul_id, into_id=merge_in.into_id)
    return schemas.SoulOut(**survivor.to_dict(request))


@require_permission("list_progress_updates")
@router.get(
    "progress_updates/",
    response={200: List[schemas.ProgressUpdateOut]},
    auth=jwt_auth
)
def progress_updates_list_api(request, params: schemas.ProgressUpdateQuery = Query(...)):
    """API endpoint to list progress updates with optional soul filter and pagination."""
    progress_updates = selectors.list_progress_updates(**params.dict())
    response = paginate_response(
        queryset=progress_updates,
        request=request,
        schema=schemas.ProgressUpdateOut,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@require_permission(
    "create_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
@router.post(
    "progress_updates/create/",
    response={201: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
def create_progress_update_api(request, progress_update_in: schemas.ProgressUpdateCreate):
    """API endpoint to create a new progress update."""

    progress_update = services.create_progress_update(data=progress_update_in.dict())
    return 201, schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@require_permission(
    "view_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
@router.get(
    "progress_updates/{progress_update_id}/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
def progress_update_details_api(request, progress_update_id: int):
    """API endpoint to retrieve details of a specific progress update by ID."""
    progress_update = selectors.get_progress_update(id=progress_update_id)
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@require_permission(
    "update_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
@router.patch(
    "progress_updates/{progress_update_id}/update/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
def update_progress_update_api(request, progress_update_id: int, progress_update_in: schemas.ProgressUpdateCreate):
    """API endpoint to update an existing progress update."""
    progress_update = services.update_progress_update(
        progress_update_id=progress_update_id,
        data=progress_update_in.dict()
    )
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@require_permission(
    "delete_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
@router.delete(
    "progress_updates/{progress_update_id}/delete/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
def delete_progress_update_api(request, progress_update_id: int):
    """API endpoint to delete a progress update by ID."""
    progress_update = services.delete_progress_update(progress_update_id=progress_update_id)
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@require_permission(
    "view_soul",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_soul_operations_handler
)

@router.get(
    "/{soul_id}/",
    response={200: schemas.SoulDetailsOut},
    auth=jwt_auth
)
def soul_details_api(request, soul_id: int):
    """API endpoint to retrieve details of a specific soul by ID."""
    soul = selectors.get_soul(soul_id=soul_id)
    return schemas.SoulDetailsOut(**soul.to_dict_details(request))
