import json
from typing import List

from django.http import JsonResponse
from ninja import Router, Query, Form

from authentication.permissions import jwt_auth
from base.api import paginate_response
from base.schemas import DetailOut
from base.utils.exceptions import CustomValidationError
from missions import schemas, services, selectors
from missions.analytics import system_wide_analytics, per_mission_analytics
from authentication.decorators import require_permission


router = Router(
    tags=["missions"],
)


@router.get(
    "locations/",
    response={200: List[schemas.LocationOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_locations")
def locations_list_api(request, filters: schemas.LocationsFilterSchema = Query(...)):
    locations = selectors.locations_list(filters=filters.dict() if filters else None)

    response = paginate_response(
        queryset=locations,
        request=request,
        schema=schemas.LocationOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "locations/create/",
    response={201: schemas.LocationOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("add_location")
def create_location_api(request, location_in: schemas.LocationCreateSchema):
    location = services.create_location(user=request.user, **location_in.dict())
    return 201, schemas.LocationOutSchema(**location.to_dict(request))


@router.patch(
    "locations/{location_id}/update/",
    response={200: schemas.LocationOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_location")
def update_location_api(request, location_id: int, location_in: schemas.LocationUpdateSchema):
    location = services.update_location(user=request.user, location_id=location_id, update_dict=location_in.dict(exclude_unset=True))
    return 200, schemas.LocationOutSchema(**location.to_dict(request))


@router.get(
    "locations/{location_id}/",
    response={200: schemas.LocationOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_location")
def location_detail_api(request, location_id: int):
    location = selectors.location_details(location_id=location_id)
    return 200, schemas.LocationOutSchema(**location.to_dict(request))


@router.delete(
    "locations/{location_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_location")
def delete_location_api(request, location_id: int):
    services.delete_location(user=request.user, location_id=location_id)
    return 204, "Location deleted successfully"


@router.get(
    "categories/",
    response={200: List[schemas.MissionCategoryOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_mission_categories")
def mission_categories_list_api(request, filters: schemas.MissionCategoryFilterSchema = Query(...)):
    categories = selectors.mission_categories_list(event_type=filters.event_type, search=filters.search)
    response = paginate_response(
        queryset=categories,
        request=request,
        schema=schemas.MissionCategoryOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "categories/create/",
    response={201: schemas.MissionCategoryOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_mission_category")
def create_missions_category_api(request, category_in: schemas.MissionCategoryCreateSchema):
    category = services.create_missions_category(user=request.user, **category_in.dict())
    return 201, schemas.MissionCategoryOutSchema(**category.to_dict())


@router.patch(
    "categories/{category_id}/update/",
    response={200: schemas.MissionCategoryOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_mission_category")
def update_mission_category_api(request, category_id: int, category_in: schemas.MissionCategoryUpdateSchema):
    category = services.update_missions_category(
        user=request.user,
        category_id=category_id,
        update_dict=category_in.dict(exclude_unset=True)
    )
    return 200, schemas.MissionCategoryOutSchema(**category.to_dict())


@router.get(
    "categories/{category_id}/",
    response={200: schemas.MissionCategoryOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_mission_category")
def mission_category_detail_api(request, category_id: int):
    category = selectors.mission_category_details(category_id=category_id)
    return 200, schemas.MissionCategoryOutSchema(**category.to_dict())


@router.delete(
    "categories/{category_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_mission_category")
def delete_mission_category_api(request, category_id: int):
    services.delete_missions_category(user=request.user, category_id=category_id)
    return 204, "Category deleted successfully"


@router.get(
    "/analytics/overview/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_admin_stats")
def system_analytics_api(request, year: int = None):
    """
    System-wide analytics report.

    Returns cumulative reports for all missions — yearly, half-year, quarterly, monthly.
    Includes age group breakdowns of souls won per period.

    Query params:
        - year (optional): Target year. Defaults to current year.
    """
    data = system_wide_analytics(year=year)
    return 200, data


@router.get(
    "/analytics/{mission_id}/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_mission_report")
def mission_analytics_api(request, mission_id: int):
    """
    Per-mission analytics report.

    Returns daily breakdown and full duration summary for a specific mission.
    Includes age group breakdowns of souls won per day.
    """
    data = per_mission_analytics(mission_id=mission_id)
    return 200, data


@router.get(
    "/",
    response={200: List[schemas.MissionOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_missions")
def missions_list_api(request, filters: schemas.MissionFilterSchema = Query(...)):
    missions = selectors.missions_list(filters=filters.dict() if filters else None)
    response = paginate_response(
        queryset=missions,
        request=request,
        schema=schemas.MissionOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/create/",
    response={201: schemas.MissionOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_mission")
def create_mission_api(request, mission_in: schemas.MissionCreateSchema = Form(...)):
    banner_file = request.FILES.get("banner_image")
    mission_in_dict = mission_in.dict()
    if banner_file:
        mission_in_dict["banner_image"] = banner_file
    user = request.user
    mission = services.create_mission(**mission_in_dict, user=user)
    return 201, schemas.MissionOutSchema(**mission.to_dict(request))


@router.patch(
    "/{mission_id}/update/",
    response={200: schemas.MissionOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_mission")
def update_mission_api(request, mission_id: int, mission_in: schemas.MissionUpdateSchema = Form(...)):
    banner_file = request.FILES.get("banner_image")
    mission_in_dict = mission_in.dict(exclude_unset=True)
    if banner_file:
        mission_in_dict["banner_image"] = banner_file
    mission = services.update_mission(user=request.user, mission_id=mission_id, update_dict=mission_in_dict)
    return 200, schemas.MissionOutSchema(**mission.to_dict(request))


@router.get(
    "/{mission_id}/",
    response={200: schemas.MissionOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_mission")
def mission_detail_api(request, mission_id: int):
    mission = selectors.mission_details(mission_id=mission_id)
    return 200, schemas.MissionOutSchema(**mission.to_dict(request))


@router.get(
    "/{mission_id}/public/",
    response={200: schemas.MinimalMissionOutSchema, 400: DetailOut},
)
def mission_detail_public_facing_api(request, mission_id: int):
    mission = selectors.mission_details(mission_id=mission_id)
    return 200, schemas.MinimalMissionOutSchema(**mission.to_dict(request))


@router.delete(
    "/{mission_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_mission")
def delete_mission_api(request, mission_id: int):
    services.delete_mission(user=request.user, mission_id=mission_id)
    return 204, "Mission deleted successfully"


@router.get(
    "/{mission_id}/participants/",
    response={200: List[schemas.MissionParticipantOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_jia_participants")
def mission_participants_list_api(
        request,
        mission_id: int,
        params: schemas.MissionParticipantsFilterSchema = Query(...)
):
    participants = selectors.mission_participants_list(
        mission_id=mission_id,
        filters=params.dict(),
        sort_by=params.sort_by,
        is_desc=params.is_desc
    )

    response = paginate_response(
        queryset=participants,
        request=request,
        schema=schemas.MissionParticipantOutSchema,
        page=params.page,
        page_size=params.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/participants/create/",
    response={201: schemas.MissionParticipantOutSchema, 400: DetailOut},
)
def create_mission_participant_api(request, participant_in: schemas.MissionParticipantCreateSchema):
    participant = services.create_mission_participant(**participant_in.dict())
    return 201, schemas.MissionParticipantOutSchema(**participant.to_dict(request))


@router.get(
    "/participants/{participant_id}/",
    response={200: schemas.MissionParticipantOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_jia_participant")
def mission_participant_detail_api(request, participant_id: int):
    participant = selectors.mission_participant_details(participant_id=participant_id)
    return 200, schemas.MissionParticipantOutSchema(**participant.to_dict(request))


@router.patch(
    "/participants/{participant_id}/update/",
    response={200: schemas.MissionParticipantOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_jia_participant")
def update_mission_participant_api(
        request,
        participant_id: int,
        participant_in: schemas.MissionParticipantUpdateSchema
):
    participant = services.update_mission_participant(
        user=request.user,
        participant_id=participant_id,
        update_dict=participant_in.dict(exclude_unset=True)
    )
    return 200, schemas.MissionParticipantOutSchema(**participant.to_dict(request))


@router.delete(
    "/participants/{participant_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_jia_participant")
def delete_mission_participant_api(request, participant_id: int):
    services.delete_mission_participant(user=request.user, participant_id=participant_id)
    return 204, "Participant deleted successfully"


@router.get(
    "/reports/",
    response={200: List[schemas.ReportOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_mission_reports")
def mission_reports_list_api(
        request,
        filters: schemas.ReportsFilterSchema = Query(...)
):
    reports = selectors.reports_list(
        filters=filters.dict() if filters else None,
        sort_by=filters.sort_by,
        is_desc=filters.is_desc
    )
    response = paginate_response(
        queryset=reports,
        request=request,
        schema=schemas.ReportOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/reports/create/",
    response={201: schemas.ReportOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_mission_report")
def create_mission_report_api(request, report_in: schemas.ReportCreateSchema = Form(...)):
    report_file = request.FILES.get("report_file")
    report_in_dict = report_in.dict()
    if report_file:
        report_in_dict["report_file"] = report_file
    else:
        raise CustomValidationError("Report file is required.")
    report = services.create_report(**report_in_dict)
    return 201, schemas.ReportOutSchema(**report.to_dict(request))


@router.get(
    "/reports/{report_id}/",
    response={200: schemas.ReportOutSchema, 400: DetailOut},
    auth=jwt_auth
)
def mission_report_detail_api(request, report_id: int):
    report = selectors.report_details(report_id=report_id)
    return 200, schemas.ReportOutSchema(**report.to_dict(request))


@router.patch(
    "/reports/{report_id}/update/",
    response={200: schemas.ReportOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_mission_report")
def update_mission_report_api(
        request,
        report_id: int,
        report_in: schemas.ReportUpdateSchema = Form(...)
):
    report_dict_in = report_in.dict(exclude_unset=True)
    report_file = request.FILES.get("report_file")
    if report_file:
        report_dict_in["report_file"] = report_file
    report = services.update_report(user=request.user, report_id=report_id, update_dict=report_dict_in)
    return 200, schemas.ReportOutSchema(**report.to_dict(request))


@router.delete(
    "/reports/{report_id}/delete/",
    response={204: str, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_mission_report")
def delete_mission_report_api(request, report_id: int):
    services.delete_report(user=request.user, report_id=report_id)
    return 204, "Mission report deleted successfully"


@router.get(
    "/gallery/images/",
    response={200: List[schemas.MissionGalleryOutSchema], 400: DetailOut},
    auth=jwt_auth
)
@require_permission("list_photo_galleries")
def mission_gallery_images_list_api(
        request,
        filters: schemas.MissionGalleryFilterSchema
):
    images = selectors.gallery_images_list(filters=filters.dict() if filters else None)
    response = paginate_response(
        queryset=images,
        request=request,
        schema=schemas.MissionGalleryOutSchema,
        page=filters.page,
        page_size=filters.page_size
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/gallery/images/create/",
    response={201: schemas.MissionGalleryOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_photo_gallery")
def create_mission_gallery_image_api(request, image_in: schemas.MissionGalleryCreateSchema = Form(...)):
    """
    Bulk upload gallery images with metadata.

    This endpoint allows uploading multiple images for a mission, each with optional
    title and description metadata. The number of metadata items must match the number
    of uploaded images.

    Form Fields:
        - mission_id (int): ID of the mission.
        - uploaded_by_id (int): ID of the user uploading the images.
        - images (file[]): One or more image files to upload.
        - images_metadata (list of objects): Metadata for each image in the same order
          as the files. Each object can have:
            - title (string, optional)
            - description (string, optional)

    Validation:
        - At least one image file is required.
        - The number of metadata objects must equal the number of files.

    Example CURL Request:

    curl -X POST "http://yourdomain.com/api/gallery/images/create/" \
      -H "Authorization: Bearer <JWT_TOKEN>" \
      -F "mission_id=1" \
      -F "uploaded_by_id=10" \
      -F "images=@/path/to/image1.jpg" \
      -F "images=@/path/to/image2.jpg" \
      -F 'images_metadata[0][title]=Front View' \
      -F 'images_metadata[0][description]=Taken in the morning' \
      -F 'images_metadata[1][title]=Side View' \
      -F 'images_metadata[1][description]=Taken in the afternoon'

    Returns:
        - 201: List of created gallery images, each including:
            - mission_id
            - title
            - description
            - image URL
            - uploaded_by_id
            - uploaded_by_name
    """
    image_files = request.FILES.getlist("images")

    if not image_files:
        raise CustomValidationError("At least one image file is required.")

    images_metadata = json.loads(image_in.images_data) if image_in.images_data else []

    if len(image_files) != len(images_metadata):
        raise CustomValidationError(
            "The number of uploaded files must match the number of metadata items."
        )

    # Combine files with metadata
    image_in_dict = image_in.dict()
    image_in_dict["image_files"] = image_files
    image_in_dict["images_metadata"] = images_metadata

    images = services.bulk_create_gallery_images(**image_in_dict)
    return 201, [schemas.MissionGalleryOutSchema(**img.to_dict(request)) for img in images]


@router.get(
    "/gallery/images/{image_id}/",
    response={200: schemas.MissionGalleryOutSchema, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("view_photo_gallery")
def mission_gallery_image_detail_api(request, image_id: int):
    image = selectors.gallery_image_details(image_id=image_id)
    return 200, schemas.MissionGalleryOutSchema(**image.to_dict(request))


@router.delete(
    "/gallery/images/delete/",
    response={204: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("delete_photo_gallery")
def delete_mission_gallery_images_api(request, image_ids: schemas.MissionGalleryDeleteSchema):
    count = services.bulk_delete_gallery_images_by_mission(
        user=request.user,
        mission_id=image_ids.mission_id,
        image_ids=image_ids.image_ids
    )
    return 204, {"detail": f"{count} Images deleted successfully"}