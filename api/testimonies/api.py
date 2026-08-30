"""
Django Ninja router for testimonies and miracles
"""
import json
from typing import List

from django.http import JsonResponse
from ninja import Router, Query, Form

from authentication.permissions import jwt_auth
from base.schemas import DetailOut
from base.api import paginate_response
from base.utils.exceptions import CustomValidationError
from authentication.decorators import require_permission

from testimonies import schemas, services, selectors

router = Router(tags=["testimonies"])
highlight_router = Router(tags=["highlights"])


def _parse_bulk_photo_upload(request, photo_in: schemas.PhotoUploadSchema) -> List[dict]:
    """Shared by testimony/miracle/highlight bulk photo endpoints — matches
    the (fixed) MissionGalleryImage bulk-upload contract."""
    image_files = request.FILES.getlist("images")
    if not image_files:
        raise CustomValidationError("At least one image file is required.")

    images_metadata = json.loads(photo_in.images_data) if photo_in.images_data else []
    if len(image_files) != len(images_metadata):
        raise CustomValidationError(
            "The number of uploaded files must match the number of metadata items."
        )

    return [
        {"image": file, "title": meta.get("title", ""), "description": meta.get("description", "")}
        for file, meta in zip(image_files, images_metadata)
    ]


@router.get(
    "/",
    response={200: List[schemas.TestimonyOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_testimonies")
def testimonies_list_api(request, filters: schemas.TestimonyAndMiracleFilterSchema = Query(...)):
    qs = selectors.testimonies_list(filters=filters.dict() if filters else None)
    response = paginate_response(
        queryset=qs,
        request=request,
        schema=schemas.TestimonyOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/create/",
    response={201: schemas.TestimonyOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_testimony")
def create_testimony_api(request, testimony_in: schemas.TestimonyCreateSchema = Form(...)):
    # handle file upload
    photo = request.FILES.get('photo')
    data = testimony_in.dict()
    if photo:
        data['photo'] = photo
    testimony = services.create_testimony(data)
    return 201, schemas.TestimonyOutSchema(**testimony.to_dict(request))


@router.get(
    "/miracles/",
    response={200: List[schemas.MiracleOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_miracles")
def miracles_list_api(request, filters: schemas.TestimonyAndMiracleFilterSchema = Query(...)):
    qs = selectors.miracles_list(filters=filters.dict() if filters else None)
    response = paginate_response(
        queryset=qs,
        request=request,
        schema=schemas.MiracleOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/miracles/create/",
    response={201: schemas.MiracleOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_miracle")
def create_miracle_api(request, miracle_in: schemas.MiracleCreateSchema = Form(...)):
    photo = request.FILES.get('photo')
    data = miracle_in.dict()
    if photo:
        data['photo'] = photo
    miracle = services.create_miracle(data)
    return 201, schemas.MiracleOutSchema(**miracle.to_dict(request))


@router.get(
    "/miracles/{miracle_id}/",
    response={200: schemas.MiracleOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_miracle")
def miracle_detail_api(request, miracle_id: int):
    miracle = selectors.miracle_details(miracle_id=miracle_id)
    return 200, schemas.MiracleOutSchema(**miracle.to_dict(request))


@router.patch(
    "/miracles/{miracle_id}/update/",
    response={200: schemas.MiracleOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_miracle",
    restricted_roles=["missioner_template"],
    restriction_handler=services.miracle_and_testimony_handler
)
def update_miracle_api(request, miracle_id: int, miracle_in: schemas.MiracleUpdateSchema = Form(...)):
    data = miracle_in.dict(exclude_unset=True)
    photo = request.FILES.get('photo')
    if photo:
        data['photo'] = photo
    miracle = services.update_miracle(miracle_id=miracle_id, update_dict=data)
    return 200, schemas.MiracleOutSchema(**miracle.to_dict(request))


@router.delete(
    "/miracles/{miracle_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_miracle")
def delete_miracle_api(request, miracle_id: int):
    services.delete_miracle(miracle_id=miracle_id)
    return 204, "Miracle deleted successfully"


@router.post(
    "/miracles/{miracle_id}/approve/",
    response={200: schemas.MiracleOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("approve_miracle")
def approve_miracle_api(request, miracle_id: int):
    miracle = services.approve_miracle(miracle_id=miracle_id)
    return 200, schemas.MiracleOutSchema(**miracle.to_dict(request))


@router.post(
    "/miracles/{miracle_id}/reject/",
    response={200: schemas.MiracleOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("reject_miracle")
def reject_miracle_api(request, miracle_id: int, reject_in: schemas.RejectSchema):
    miracle = services.reject_miracle(miracle_id=miracle_id, reason=reject_in.reason)
    return 200, schemas.MiracleOutSchema(**miracle.to_dict(request))


@router.get(
    "/{testimony_id}/",
    response={200: schemas.TestimonyOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_testimony")
def testimony_detail_api(request, testimony_id: int):
    testimony = selectors.testimony_details(testimony_id=testimony_id)
    return 200, schemas.TestimonyOutSchema(**testimony.to_dict(request))


@router.patch(
    "/{testimony_id}/update/",
    response={200: schemas.TestimonyOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_testimony",
    restricted_roles=["missioner_template"],
    restriction_handler=services.miracle_and_testimony_handler
)
def update_testimony_api(request, testimony_id: int, testimony_in: schemas.TestimonyUpdateSchema = Form(...)):
    data = testimony_in.dict(exclude_unset=True)
    photo = request.FILES.get('photo')
    if photo:
        data['photo'] = photo
    testimony = services.update_testimony(testimony_id=testimony_id, update_dict=data)
    return 200, schemas.TestimonyOutSchema(**testimony.to_dict(request))


@router.delete(
    "/{testimony_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_testimony")
def delete_testimony_api(request, testimony_id: int):
    services.delete_testimony(testimony_id=testimony_id)
    return 204, "Testimony deleted successfully"


@router.post(
    "/{testimony_id}/approve/",
    response={200: schemas.TestimonyOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("approve_testimony")
def approve_testimony_api(request, testimony_id: int):
    testimony = services.approve_testimony(testimony_id=testimony_id)
    return 200, schemas.TestimonyOutSchema(**testimony.to_dict(request))


@router.post(
    "/{testimony_id}/reject/",
    response={200: schemas.TestimonyOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("reject_testimony")
def reject_testimony_api(request, testimony_id: int, reject_in: schemas.RejectSchema):
    testimony = services.reject_testimony(testimony_id=testimony_id, reason=reject_in.reason)
    return 200, schemas.TestimonyOutSchema(**testimony.to_dict(request))


@router.post(
    "/{testimony_id}/photos/create/",
    response={201: List[schemas.TestimonyPhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_testimony",
    restricted_roles=["missioner_template"],
    restriction_handler=services.testimony_photo_restriction_handler
)
def create_testimony_photos_api(request, testimony_id: int, photo_in: schemas.PhotoUploadSchema = Form(...)):
    images_data = _parse_bulk_photo_upload(request, photo_in)
    photos = services.bulk_create_testimony_photos(testimony_id=testimony_id, images_data=images_data)
    return 201, [schemas.TestimonyPhotoOutSchema(**p.to_dict(request)) for p in photos]


@router.get(
    "/{testimony_id}/photos/",
    response={200: List[schemas.TestimonyPhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_testimony")
def testimony_photos_list_api(request, testimony_id: int):
    photos = selectors.testimony_photos_list(testimony_id=testimony_id)
    return 200, [schemas.TestimonyPhotoOutSchema(**p.to_dict(request)) for p in photos]


@router.post(
    "/miracles/{miracle_id}/photos/create/",
    response={201: List[schemas.MiraclePhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_miracle",
    restricted_roles=["missioner_template"],
    restriction_handler=services.miracle_photo_restriction_handler
)
def create_miracle_photos_api(request, miracle_id: int, photo_in: schemas.PhotoUploadSchema = Form(...)):
    images_data = _parse_bulk_photo_upload(request, photo_in)
    photos = services.bulk_create_miracle_photos(miracle_id=miracle_id, images_data=images_data)
    return 201, [schemas.MiraclePhotoOutSchema(**p.to_dict(request)) for p in photos]


@router.get(
    "/miracles/{miracle_id}/photos/",
    response={200: List[schemas.MiraclePhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_miracle")
def miracle_photos_list_api(request, miracle_id: int):
    photos = selectors.miracle_photos_list(miracle_id=miracle_id)
    return 200, [schemas.MiraclePhotoOutSchema(**p.to_dict(request)) for p in photos]


# --- Highlights (separate top-level /api/highlights/ router, per GIK-02 §6) ---

@highlight_router.get(
    "/",
    response={200: List[schemas.HighlightOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_highlights")
def highlights_list_api(request, filters: schemas.TestimonyAndMiracleFilterSchema = Query(...)):
    qs = selectors.highlights_list(filters=filters.dict() if filters else None)
    response = paginate_response(
        queryset=qs,
        request=request,
        schema=schemas.HighlightOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@highlight_router.post(
    "/create/",
    response={201: schemas.HighlightOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_highlight")
def create_highlight_api(request, highlight_in: schemas.HighlightCreateSchema = Form(...)):
    photo = request.FILES.get('photo')
    data = highlight_in.dict()
    if photo:
        data['photo'] = photo
    highlight = services.create_highlight(data)
    return 201, schemas.HighlightOutSchema(**highlight.to_dict(request))


@highlight_router.get(
    "/{highlight_id}/",
    response={200: schemas.HighlightOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_highlight")
def highlight_detail_api(request, highlight_id: int):
    highlight = selectors.highlight_details(highlight_id=highlight_id)
    return 200, schemas.HighlightOutSchema(**highlight.to_dict(request))


@highlight_router.patch(
    "/{highlight_id}/update/",
    response={200: schemas.HighlightOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_highlight",
    restricted_roles=["missioner_template"],
    restriction_handler=services.miracle_and_testimony_handler
)
def update_highlight_api(request, highlight_id: int, highlight_in: schemas.HighlightUpdateSchema = Form(...)):
    data = highlight_in.dict(exclude_unset=True)
    photo = request.FILES.get('photo')
    if photo:
        data['photo'] = photo
    highlight = services.update_highlight(highlight_id=highlight_id, update_dict=data)
    return 200, schemas.HighlightOutSchema(**highlight.to_dict(request))


@highlight_router.delete(
    "/{highlight_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_highlight")
def delete_highlight_api(request, highlight_id: int):
    services.delete_highlight(highlight_id=highlight_id)
    return 204, "Highlight deleted successfully"


@highlight_router.post(
    "/{highlight_id}/approve/",
    response={200: schemas.HighlightOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("approve_highlight")
def approve_highlight_api(request, highlight_id: int):
    highlight = services.approve_highlight(highlight_id=highlight_id)
    return 200, schemas.HighlightOutSchema(**highlight.to_dict(request))


@highlight_router.post(
    "/{highlight_id}/reject/",
    response={200: schemas.HighlightOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("reject_highlight")
def reject_highlight_api(request, highlight_id: int, reject_in: schemas.RejectSchema):
    highlight = services.reject_highlight(highlight_id=highlight_id, reason=reject_in.reason)
    return 200, schemas.HighlightOutSchema(**highlight.to_dict(request))


@highlight_router.post(
    "/{highlight_id}/photos/create/",
    response={201: List[schemas.HighlightPhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission(
    "update_highlight",
    restricted_roles=["missioner_template"],
    restriction_handler=services.highlight_photo_restriction_handler
)
def create_highlight_photos_api(request, highlight_id: int, photo_in: schemas.PhotoUploadSchema = Form(...)):
    images_data = _parse_bulk_photo_upload(request, photo_in)
    photos = services.bulk_create_highlight_photos(highlight_id=highlight_id, images_data=images_data)
    return 201, [schemas.HighlightPhotoOutSchema(**p.to_dict(request)) for p in photos]


@highlight_router.get(
    "/{highlight_id}/photos/",
    response={200: List[schemas.HighlightPhotoOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_highlight")
def highlight_photos_list_api(request, highlight_id: int):
    photos = selectors.highlight_photos_list(highlight_id=highlight_id)
    return 200, [schemas.HighlightPhotoOutSchema(**p.to_dict(request)) for p in photos]
