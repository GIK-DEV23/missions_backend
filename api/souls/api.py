
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


@router.get(
    "/",
    response={200: List[schemas.SoulOut]},
    auth=jwt_auth
)
@require_permission("list_souls")
def souls_list_api(request, params: schemas.SoulsQuery = Query(...)):
    """API endpoint to list souls with optional filters and pagination.
    
    Phone numbers are masked by default for privacy. Use the /reveal_phone/{soul_id}
    endpoint to get the unmasked phone number for a specific soul.
    """
    filters = params.dict(exclude={'follow_up_health', 'sort_by', 'is_desc', 'page', 'page_size', 'minors_without_consent'})
    souls = selectors.list_souls(
        user=request.user,
        filters=filters,
        sort_by=params.sort_by,
        is_desc=params.is_desc,
        follow_up_health=params.follow_up_health,
        minors_without_consent=params.minors_without_consent or False,
    )
    response = paginate_response(
        queryset=souls,
        request=request,
        schema=schemas.SoulOut,
        page=params.page,
        page_size=params.page_size,
        to_dict_kwargs={'mask_phone': True}  # Always mask phones in list view
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/stats/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("soul_stats")
def souls_stats_api(request, params: schemas.SoulsQuery = Query(...)):
    """API endpoint to list souls with optional filters and pagination."""
    souls_count = selectors.souls_stats(
        user=request.user,
        filters=params.dict()
    )
    return 200, souls_count


@router.post(
    "create/",
    response={201: schemas.SoulOut},
    auth=jwt_auth
)
@require_permission("create_soul")
def create_soul_api(request, soul_in: schemas.SoulCreate):
    """API endpoint to create a new soul."""
    soul = services.create_soul(user=request.user, data=soul_in.dict())
    return 201, schemas.SoulOut(**soul.to_dict(request))


@router.post(
    "/upload_souls/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("upload_souls")
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


@router.patch(
    "/{soul_id}/update/",
    response={200: schemas.SoulOut},
    auth=jwt_auth
)
@require_permission("update_soul")
def update_soul_api(request, soul_id: int, soul_in: schemas.SoulUpdate):
    """API endpoint to update an existing soul."""
    soul = services.update_soul(user=request.user, soul_id=soul_id, data=soul_in.dict())
    return schemas.SoulOut(**soul.to_dict(request))


@router.delete(
    "/{soul_id}/delete/",
    response={200: schemas.SoulOut},
    auth=jwt_auth
)
@require_permission("delete_soul")
def delete_soul_api(request, soul_id: int):
    """API endpoint to delete a soul by ID."""
    soul = services.delete_soul(user=request.user, soul_id=soul_id)
    return schemas.SoulOut(**soul.to_dict(request))


@router.post(
    "/{soul_id}/merge/",
    response={200: schemas.SoulOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("merge_soul")
def merge_soul_api(request, soul_id: int, merge_in: schemas.SoulMergeIn):
    """Merge a duplicate soul into another, reassigning its history."""
    survivor = services.merge_souls(user=request.user, soul_id=soul_id, into_id=merge_in.into_id)
    return schemas.SoulOut(**survivor.to_dict(request))


@router.get(
    "progress_updates/",
    response={200: List[schemas.ProgressUpdateOut]},
    auth=jwt_auth
)
@require_permission("list_progress_updates")
def progress_updates_list_api(request, params: schemas.ProgressUpdateQuery = Query(...)):
    """API endpoint to list progress updates with optional soul filter and pagination."""
    # Only pass selector-relevant params (exclude pagination fields from BaseQuery)
    progress_updates = selectors.list_progress_updates(
        soul_id=params.soul_id,
        is_desc=params.is_desc if params.is_desc is not None else True
    )
    response = paginate_response(
        queryset=progress_updates,
        request=request,
        schema=schemas.ProgressUpdateOut,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "progress_updates/create/",
    response={201: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
@require_permission(
    "create_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
def create_progress_update_api(request, progress_update_in: schemas.ProgressUpdateCreate):
    """API endpoint to create a new progress update."""

    progress_update = services.create_progress_update(data=progress_update_in.dict())
    return 201, schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@router.get(
    "progress_updates/{progress_update_id}/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
@require_permission(
    "view_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
def progress_update_details_api(request, progress_update_id: int):
    """API endpoint to retrieve details of a specific progress update by ID."""
    progress_update = selectors.get_progress_update(id=progress_update_id)
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@router.patch(
    "progress_updates/{progress_update_id}/update/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
@require_permission(
    "update_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
def update_progress_update_api(request, progress_update_id: int, progress_update_in: schemas.ProgressUpdateCreate):
    """API endpoint to update an existing progress update."""
    progress_update = services.update_progress_update(
        progress_update_id=progress_update_id,
        data=progress_update_in.dict()
    )
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@router.delete(
    "progress_updates/{progress_update_id}/delete/",
    response={200: schemas.ProgressUpdateOut},
    auth=jwt_auth
)
@require_permission(
    "delete_progress_update",
    restricted_roles=["missioner_template"],
    restriction_handler=progress_update_handler
)
def delete_progress_update_api(request, progress_update_id: int):
    """API endpoint to delete a progress update by ID."""
    progress_update = services.delete_progress_update(progress_update_id=progress_update_id)
    return schemas.ProgressUpdateOut(**progress_update.to_dict(request))


@router.get(
    "/{soul_id}/",
    response={200: schemas.SoulDetailsOut},
    auth=jwt_auth
)
@require_permission(
    "view_soul",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_soul_operations_handler
)
def soul_details_api(request, soul_id: int):
    """API endpoint to retrieve details of a specific soul by ID."""
    soul = selectors.get_soul(soul_id=soul_id)
    return schemas.SoulDetailsOut(**soul.to_dict_details(request))


@router.get(
    "/{soul_id}/reveal_phone/",
    response={200: schemas.PhoneRevealOut},
    auth=jwt_auth
)
@require_permission(
    "view_soul",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_soul_operations_handler
)
def reveal_phone_api(request, soul_id: int):
    """API endpoint to reveal the unmasked phone number for a specific soul.
    
    This is a separate endpoint for audit purposes - accessing unmasked phone
    numbers is tracked separately from viewing soul details.
    """
    soul = selectors.get_soul(soul_id=soul_id)
    return schemas.PhoneRevealOut(
        soul_id=soul.id,
        phone_number=str(soul.phone_number) if soul.phone_number else None,
        guardian_phone=str(soul.guardian_phone) if soul.guardian_phone else None,
    )


@router.get(
    "/{soul_id}/activity/",
    response={200: List[schemas.ProgressUpdateOut]},
    auth=jwt_auth
)
@require_permission(
    "view_soul",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_soul_operations_handler
)
def soul_activity_api(request, soul_id: int, params: schemas.ProgressUpdateQuery = Query(...)):
    """API endpoint to retrieve all progress updates for a specific soul."""
    activity = selectors.get_soul_activity(soul_id=soul_id)
    response = paginate_response(
        queryset=activity,
        request=request,
        schema=schemas.ProgressUpdateOut,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/{soul_id}/assignments/",
    response={200: List[schemas.SoulAssignmentOut]},
    auth=jwt_auth
)
@require_permission(
    "view_soul",
    restricted_roles=["missioner_template"],
    restriction_handler=missioner_soul_operations_handler
)
def soul_assignments_list_api(request, soul_id: int):
    """List all assignments for a soul."""
    assignments = selectors.list_soul_assignments(soul_id=soul_id)
    return [schemas.SoulAssignmentOut(**a.to_dict(request)) for a in assignments]


@router.post(
    "/{soul_id}/assignments/",
    response={201: schemas.SoulAssignmentOut},
    auth=jwt_auth
)
@require_permission("assign_soul")
def create_soul_assignment_api(request, soul_id: int, assignment_in: schemas.SoulAssignmentCreate):
    """Assign a user to follow up with a soul."""
    data = assignment_in.dict()
    data["soul_id"] = soul_id
    assignment = services.create_soul_assignment(user=request.user, data=data)
    return 201, schemas.SoulAssignmentOut(**assignment.to_dict(request))


@router.patch(
    "/assignments/{assignment_id}/",
    response={200: schemas.SoulAssignmentOut},
    auth=jwt_auth
)
@require_permission("assign_soul")
def update_soul_assignment_api(request, assignment_id: int, assignment_in: schemas.SoulAssignmentUpdate):
    """Update an assignment (e.g., deactivate or add notes)."""
    data = {k: v for k, v in assignment_in.dict().items() if v is not None}
    assignment = services.update_soul_assignment(assignment_id=assignment_id, data=data)
    return schemas.SoulAssignmentOut(**assignment.to_dict(request))
