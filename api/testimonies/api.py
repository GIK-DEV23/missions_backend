"""
Django Ninja router for testimonies and miracles
"""
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
