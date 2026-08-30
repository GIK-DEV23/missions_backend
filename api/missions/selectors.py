from typing import Optional, Dict, Any

from django.db import models

from base.utils.exceptions import CustomValidationError
from base.utils.helpers import apply_sorting
from django.db.models import Count, Q
from missions.constants import EventType
from missions.filters import LocationFilter, MissionFilter, MissionJIAFilter, ReportsFilter, MissionGalleryFilter
from missions.models import MissionCategory, Location, Mission, MissionJIAParticipant, Report, MissionGallery

from souls.constants import JourneyStage


def location_details(location_id: int) -> Location:
    """
    Get details of a location by ID.

    Args:
        location_id: ID of the location.

    Returns:
        Location instance or None if not found.
    """
    try:
        return Location.objects.get(id=location_id)
    except Location.DoesNotExist:
        raise CustomValidationError("Location with the given ID does not exist.")


def locations_list(filters: Optional[Dict[str, Any]] = None) -> models.QuerySet:
    """
    List locations with optional filters.

    Args:
        filters: Optional dictionary of filters.

    Returns:
        QuerySet of Location instances.
    """
    qs = Location.objects.all().select_related('parent_location').order_by('name')
    return LocationFilter(filters, qs).qs if filters else qs


def mission_category_details(category_id: int) -> Optional[MissionCategory]:
    """
    Get details of a mission category by ID.

    Args:
        category_id: ID of the category.

    Returns:
        MissionCategory instance or None if not found.
    """
    try:
        return MissionCategory.objects.get(id=category_id)
    except MissionCategory.DoesNotExist:
        raise CustomValidationError("MissionCategory with the given ID does not exist.")


def mission_categories_list(search: Optional[str] = None, event_type: Optional[EventType] = None) -> models.QuerySet:
    """
    List mission categories with optional filters.

    Args:
        search: Optional dictionary.
        event_type: Optional EventType to filter by.

    Returns:
        QuerySet of MissionCategory instances.
    """
    qs = MissionCategory.objects.all().order_by('name')
    if search:
        qs.filter(name__icontains=search)
    if event_type:
        qs = qs.filter(event_type=event_type.value)
    return qs


def mission_details(mission_id: int) -> Mission:
    """
    Get details of a mission by ID.

    Args:
        mission_id: ID of the mission.

    Returns:
        Mission instance or None if not found.
    """
    error_message = "Mission with the given ID does not exist."
    try:
        mission = (
            Mission.objects
            .annotate(
                souls_won_count=Count("souls", filter=Q(souls__status=JourneyStage.NEW_BELIEVER)),
                souls_followup_count=Count("souls", filter=Q(souls__status=JourneyStage.GROWING)),
                participants_count=Count("participants", filter=Q(participants__is_archived=False)),
            )
            .select_related("category", "location")
            .get(id=mission_id)
        )

        if mission.is_archived:
            raise CustomValidationError(error_message)

        return mission
    except Mission.DoesNotExist:
        raise CustomValidationError(error_message)


def missions_list(filters: Optional[Dict[str, Any]] = None) -> models.QuerySet:
    """
    List missions with optional filters.

    Args:
        filters: Optional dictionary of filters.

    Returns:
        QuerySet of Mission instances.
    """
    qs = (
        Mission.objects
        .filter(is_archived=False)
        .select_related('category', 'location')
        .annotate(
            souls_won_count=Count("souls", filter=Q(souls__status=JourneyStage.NEW_BELIEVER)),
            souls_followup_count=Count("souls", filter=Q(souls__status=JourneyStage.GROWING)),
        )
        .order_by('-start_date')
    )

    if filters:
        if 'status' in filters and filters['status'] is not None:
            filters['status'] = filters['status'].value

    return MissionFilter(filters, qs).qs if filters else qs


def mission_participant_details(participant_id: int) -> MissionJIAParticipant:
    """
    Get details of a mission participant by ID.

    Args:
        participant_id: ID of the participant.

    Returns:
        MissionJIAParticipant instance or None if not found.
    """
    error_message = "Mission participant with the given ID does not exist."
    try:
        mission = MissionJIAParticipant.objects.get(id=participant_id)
        if mission.is_archived:
            raise CustomValidationError(error_message)
        return mission
    except MissionJIAParticipant.DoesNotExist:
        raise CustomValidationError(error_message)


def mission_participants_list(
    mission_id: int,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = 'created_at',
    is_desc: bool = True
) -> models.QuerySet:
    """
    List mission participants with optional filters.

    Args:
        mission_id: ID of the mission to filter by.
        filters: Optional dictionary of filters.
        sort_by: Optional field to sort by. Defaults to 'created_at'.
        is_desc: Optional boolean to indicate descending order. Defaults to True.

    Returns:
        QuerySet of MissionJIAParticipant instances.
    """
    qs = MissionJIAParticipant.objects.filter(mission__id=mission_id).select_related('mission', 'user')
    qs = apply_sorting(
        qs,
        sort_by=sort_by,
        is_desc=is_desc,
        allowed_fields=['created_at', 'full_name', 'phone_number', 'travelling_from']
    )
    print("JIA Filters:", filters)

    if filters:
        # Convert enum to its string value
        if 'gender' in filters and filters['gender'] is not None:
            filters['gender'] = filters['gender'].value

    return MissionJIAFilter(filters, qs).qs if filters else qs


def my_registrations(user) -> models.QuerySet:
    """MissionParticipant rows for the authenticated user (GET /api/registrations/mine/)."""
    return MissionJIAParticipant.objects.filter(
        user=user, is_archived=False
    ).select_related('mission', 'user').order_by('-created_at')


def report_details(report_id: int) -> Report:
    """
    Get details of a report by ID.

    Args:
        report_id: ID of the report.

    Returns:
        Report instance or None if not found.
    """
    error_message = "Report with the given ID does not exist."
    try:
        report = Report.objects.get(id=report_id)
        if report.is_archived:
            raise CustomValidationError(error_message)
        return report
    except Report.DoesNotExist:
        raise CustomValidationError(error_message)


def reports_list(
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'created_at',
        is_desc: bool = True
) -> models.QuerySet:
    """
    List reports with optional filters.

    Args:
        filters: Optional dictionary of filters.
        sort_by: Optional field to sort by. Defaults to 'created_at'.
        is_desc: Optional boolean to indicate descending order. Defaults to True.

    Returns:
        QuerySet of Report instances.
    """
    qs = Report.objects.filter(is_archived=True).select_related('mission', 'created_by')
    qs = apply_sorting(
        qs,
        sort_by=sort_by,
        is_desc=is_desc,
        allowed_fields=['created_at', 'title']
    )
    return ReportsFilter(filters, qs).qs if filters else qs


def gallery_image_details(image_id: int) -> MissionGallery:
    """
    Get details of a gallery image by ID.

    Args:
        image_id: ID of the gallery image.

    Returns:
        MissionGallery instance or None if not found.
    """
    try:
        return MissionGallery.objects.get(id=image_id)
    except MissionGallery.DoesNotExist:
        raise CustomValidationError("MissionGallery with the given ID does not exist.")


def gallery_images_list(
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = 'created_at',
    is_desc: bool = True
) -> models.QuerySet:
    """
    List gallery images with optional mission filter.

    Args:
        mission_id: Optional ID of the mission to filter by.
        sort_by: Optional field to sort by. Defaults to 'created_at'.
        is_desc: Optional boolean to indicate descending order. Defaults to True.

    Returns:
        QuerySet of MissionGallery instances.
    """
    qs = MissionGallery.objects.all().select_related('mission', 'uploaded_by')
    qs = apply_sorting(
        qs,
        sort_by=sort_by,
        is_desc=is_desc,
        allowed_fields=['created_at', 'title']
    )
    return MissionGalleryFilter(filters, qs).qs if filters else qs
