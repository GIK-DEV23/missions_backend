import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

from django.db import IntegrityError
from django.utils import timezone

from audit_logs.schemas import ActionType
from audit_logs.services import log_audit_event
from base.utils.exceptions import CustomValidationError, parse_integrity_error
from base.utils.helpers import serialize_types
from missions.constants import EventType
from missions.models import MissionCategory, Mission, MissionJIAParticipant, Report, MissionGallery, Location
from missions.selectors import mission_category_details, location_details, mission_details, \
    mission_participant_details, report_details
from users.selectors import user_details


def create_location(
    user,
    name: str,
    category: str,
    description: str = "",
    parent_location_id: Optional[int] = None
) -> Location:
    """
    Create a new location.

    Args:
        user: User creating the location.
        name: Name of the location.
        category: Category of the location.
        description: Description of the location.
        parent_location_id: ID of the parent location (optional).

    Returns:
        Created Location instance.
    """
    parent_location = None
    if category in ["county", "town"] and not parent_location_id:
        raise CustomValidationError("Parent location is required for county and town categories.")
    if category == "town" and not description:
        raise CustomValidationError("Description is required for town category.")
    if parent_location_id:
        parent_location = location_details(parent_location_id)
    if category == "country" and parent_location:
        raise CustomValidationError("Country category cannot have a parent location.")
    if category == "county" and parent_location and parent_location.category != "country":
        raise CustomValidationError("Parent location for county must be a country.")
    location, _ = Location.objects.get_or_create(
        name=name,
        category=category,
        description=description,
        parent_location=parent_location
    )
    log_audit_event(
        user=user,
        action_category="locations",
        action_type=ActionType.CREATION,
        action_description=f"{user.email} created location '{location.pk}:{location.name}'",
        is_successful=True
    )
    return location


def update_location(user, update_dict: Dict[str, Any], location_id: int) -> Location:
    """
    Update a location.

    Args:
        user: User performing the update.
        update_dict: Dictionary of fields to update.
        location_id: ID of the location to update.
    """
    location = location_details(location_id)
    original_values = {
        key: getattr(location, key)
        for key in update_dict.keys()
        if hasattr(location, key)
    }
    if 'parent_location_id' in update_dict:
        parent_location = location_details(update_dict.pop('parent_location_id'))
        location.parent_location = parent_location

    for key, value in update_dict.items():
        setattr(location, key, value)
    changed_fields = []
    for key, old_value in original_values.items():
        new_value = getattr(location, key)
        if old_value != new_value:
            changed_fields.append(f"{key}: '{old_value}' → '{new_value}'")
    location.save()
    if changed_fields:
        changes_text = ", ".join(changed_fields)
        log_description = (
            f"{user.email} updated location '{location.pk}:{location.name}' "
            f"Changes: {changes_text}"
        )
        log_audit_event(
            action_category="locations",
            action_type=ActionType.MODIFICATION,
            action_description=log_description,
            is_successful=True,
            user=user
        )
    return location


def delete_location(user, location_id: int) -> Location:
    """
    Delete a location.

    Args:
        user: User performing the deletion.
        location_id: ID of the location to delete.
    """
    location = location_details(location_id)
    location.delete()
    log_audit_event(
        action_category="locations",
        action_type=ActionType.DELETION,
        action_description=f"{user.email} deleted location '{location.pk}:{location.name}'",
        is_successful=True,
        user=user
    )
    return location


def create_missions_category(user, name: str, description: str = "", event_type: Optional[EventType] = None) -> MissionCategory:
    """
    Create a mission category if it doesn't exist.

    Args:
        user: User creating the category.
        name: Name of the category.
        description: Description of the category.
        event_type: Event type of the category.
    """
    category, created = MissionCategory.objects.get_or_create(
        name=name,
        defaults={
            "description": description,
            "event_type": event_type.value
        }
    )
    if created:
        log_audit_event(
            user=user,
            action_category="mission_categories",
            action_type=ActionType.CREATION,
            action_description=f"{user.email} created mission category '{category.pk}:{category.name}'",
            is_successful=True
        )
    return category


def update_missions_category(user, update_dict: Dict[str, Any], category_id: int) -> MissionCategory:
    """
    Update a mission category.

    Args:
        user: User performing the update.
        update_dict: Dictionary of fields to update.
        category_id: ID of the category to update.
    """
    category = mission_category_details(category_id)
    original_values = {
        key: getattr(category, key)
        for key in update_dict.keys()
        if hasattr(category, key)
    }
    for key, value in update_dict.items():
        if key == 'event_type' and value is not None:
            value = value.value
        setattr(category, key, value)
    changed_fields = []
    for key, old_value in original_values.items():
        new_value = getattr(category, key)
        if old_value != new_value:
            changed_fields.append(f"{key}: '{old_value}' → '{new_value}'")
    category.save()
    if changed_fields:
        changes_text = ", ".join(changed_fields)
        log_description = (
            f"{user.email} updated mission category '{category.pk}:{category.name}' "
            f"Changes: {changes_text}"
        )
        log_audit_event(
            action_category="mission_categories",
            action_type=ActionType.MODIFICATION,
            action_description=log_description,
            is_successful=True,
            user=user
        )
    return category


def delete_missions_category(user, category_id: int) -> MissionCategory:
    """
    Delete a mission category.

    Args:
        user: User performing the deletion.
        category_id: ID of the category to delete.
    """
    category = mission_category_details(category_id)
    category.delete()
    log_audit_event(
        user=user,
        action_category="mission_categories",
        action_type=ActionType.DELETION,
        action_description=f"{user.email} deleted mission category '{category.pk}:{category.name}'",
        is_successful=True
    )
    return category


def create_mission(
    title: str,
    description: str,
    category_id: int,
    location_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    user,
    partnering_organization: Optional[list[Dict]] = None,
    registration_close_date: Optional[datetime.date] = None,
    registration_fee_required: Optional[bool] = True,
    registration_fee: Optional[Decimal] = None,
    couple_registration_fee: Optional[Decimal] = None,
    banner_image=None,
    client_id: Optional[uuid.UUID] = None
) -> Mission:
    """
    Create a new mission.
    Args:
        user: User creating the mission.
        title: Title of the mission.
        description: Description of the mission.
        category_id: MissionCategory id.
        location_id: Location id.
        start_date: Start date of the mission.
        end_date: End date of the mission.
        partnering_organization: List of partnering organizations.
        registration_fee_required: Is registration fee required for the mission.
        registration_close_date: Registration close date for the mission.
        registration_fee: Registration fee for the mission.
        couple_registration_fee: Couple registration fee for the mission.
        banner_image: Banner image for the mission.

    Returns:
        Created Mission instance.
    """

    if start_date > end_date:
        raise CustomValidationError("Start date cannot be after end date.")
    today = timezone.now().date()

    if registration_close_date and registration_close_date < today:
        raise CustomValidationError("Registration close date cannot be in the past.")

    category = mission_category_details(category_id)
    location = location_details(location_id)
    mission, _ = Mission.objects.get_or_create(
        title=title,
        description=description,
        category=category,
        location=location,
        start_date=start_date,
        end_date=end_date,
        partnering_organization=partnering_organization or [],
        registration_close_date=registration_close_date,
        registration_fee_required=registration_fee_required,
        registration_fee=registration_fee,
        couple_registration_fee=couple_registration_fee,
        banner_image=banner_image,
        created_by=user,
        client_id=client_id
    )
    return mission


def update_mission(user, update_dict: Dict[str, Any], mission_id: int) -> Mission:
    """
    Update a mission.

    Args:
        user: User performing the update.
        update_dict: Dictionary of fields to update.
        mission_id: ID of the mission to update.
    """
    mission = mission_details(mission_id)
    original_values = {
        key: getattr(mission, key)
        for key in update_dict.keys()
        if hasattr(mission, key)
    }
    if 'start_date' in update_dict and 'end_date' in update_dict:
        if update_dict['start_date'] > update_dict['end_date']:
            raise CustomValidationError("Start date cannot be after end date.")
    elif 'start_date' in update_dict:
        if update_dict['start_date'] > mission.end_date:
            raise CustomValidationError("Start date cannot be after end date.")
    elif 'end_date' in update_dict:
        if mission.start_date >= update_dict['end_date']:
            raise CustomValidationError("Start date cannot be after end date.")

    if 'category_id' in update_dict:
        category = mission_category_details(update_dict.pop('category_id'))
        mission.category = category

    if 'location_id' in update_dict:
        location = location_details(update_dict.pop('location_id'))
        mission.location = location

    for key, value in update_dict.items():
        setattr(mission, key, value)
    changed_fields = []
    for key, old_value in original_values.items():
        new_value = getattr(mission, key)
        if old_value != new_value:
            changed_fields.append(f"{key}: '{old_value}' → '{new_value}'")
    mission.save()
    if changed_fields:
        changes_text = ", ".join(changed_fields)
        log_description = (
            f"{user.email} updated mission '{mission.pk}:{mission.title}' "
            f"Changes: {changes_text}"
        )
        log_audit_event(
            action_category="missions",
            action_type=ActionType.MODIFICATION,
            action_description=log_description,
            is_successful=True,
            user=user
        )
    return mission


def delete_mission(user, mission_id: int) -> Mission:
    """
    Delete a mission.

    Args:
        user: User performing the deletion.
        mission_id: ID of the mission to delete.
    """
    mission = mission_details(mission_id)
    mission.is_archived = True
    log_description = f"{user.email} deleted mission '{mission.pk}:{mission.title}'"
    mission.save()
    log_audit_event(
        action_category="missions",
        action_type=ActionType.DELETION,
        action_description=log_description,
        is_successful=True,
        user=user
    )
    return mission


def get_mission_registration_fee(mission: Mission, is_couple: bool = False) -> Decimal:
    """
    Get the registration fee for a mission.

    Args:
        mission: ID of the mission.
        is_couple: Whether the participant is coming as a couple.
    """
    if is_couple:
        fee = mission.couple_registration_fee or Decimal(0)
    else:
        fee = mission.registration_fee or Decimal(0)
    return fee


def create_mission_participant(
    mission_id: int,
    travelling_from: str,
    days_of_attendance: list[dict[str, Any]],
    gender: str,
    full_name: str | None = None,
    phone_number: str | None = None,
    diet_advisory: str | None = None,
    need_facilitation: bool = False,
    facilitation_amount: Decimal | None = None,
    user_id: int | None = None,
    coming_as_couple: bool | None = False,
    partner_name: str | None = "",
    client_id: uuid.UUID | None = None
):
    if not full_name and not user_id:
        raise CustomValidationError("Either full name or user id must be provided.")
    if facilitation_amount is None:
        facilitation_amount = Decimal(0)
    user = user_details(user_id) if user_id else None
    mission = mission_details(mission_id)

    if not phone_number and (not user or not user.phone_number):
        raise CustomValidationError("Phone number is a required field")

    if coming_as_couple and not partner_name:
        raise CustomValidationError("Partner name is required when coming as a couple.")

    if need_facilitation and not facilitation_amount:
        raise CustomValidationError("Facilitation amount is required.")

    if facilitation_amount and not need_facilitation:
        raise CustomValidationError("Facilitation amount not needed")

    mission_fee = get_mission_registration_fee(mission, coming_as_couple)

    if facilitation_amount < 0 or facilitation_amount > mission_fee:
        raise CustomValidationError("Invalid facilitation amount.")

    mission = mission_details(mission_id=mission_id)
    today = timezone.now().date()

    if mission.registration_close_date and mission.registration_close_date < today:
        raise CustomValidationError("Registration for this mission is closed.")

    mission_start = mission.start_date
    mission_end = mission.end_date
    print(mission_start, mission_end)
    total_days = (mission_end - mission_start).days + 1
    print("Total days in mission:", total_days)
    for day_info in days_of_attendance:
        day = day_info.get("day")
        day_date = day_info.get("day_date")

        if day is None or not (1 <= day <= total_days):
            raise CustomValidationError(f"Day {day} is out of range (must be 1–{total_days}).")

        if day_date:
            # Normalize to date if datetime provided
            if hasattr(day_date, "date"):
                day_date = day_date.date()

            if not (mission_start <= day_date <= mission_end):
                raise CustomValidationError(f"Day date {day_date} is out of range. The mission starts on {mission_start} and ends on {mission_end}.")

            # Expected date from mission start
            expected_date = mission_start + timedelta(days=day - 1)
            if day_date != expected_date:
                raise CustomValidationError(
                    f"Day {day} mismatch: expected {expected_date}, got {day_date}"
                )

        # Check duplicates
        if days_of_attendance.count(day_info) > 1:
            raise CustomValidationError(f"Duplicate entry for day {day} in days_of_attendance.")

    days_of_attendance = serialize_types(days_of_attendance)
    # Add check to avoid duplicate participants with same phone number and full name for the same mission
    try:
        participant = MissionJIAParticipant.objects.create(
            mission=mission,
            user=user,
            full_name=full_name or user.get_full_name(),
            phone_number=phone_number or user.phone_number,
            travelling_from=travelling_from,
            diet_advisory=diet_advisory,
            days_of_attendance=sorted(days_of_attendance, key=lambda x: x["day"]),
            need_facilitation=need_facilitation,
            facilitation_amount=facilitation_amount,
            gender=gender,
            coming_as_couple=coming_as_couple,
            partner_name=partner_name,
            client_id=client_id
        )
    except IntegrityError as e:
        raise CustomValidationError(parse_integrity_error(e))
    except Exception as e:
        raise CustomValidationError(str(e))

    return participant


def update_mission_participant(user, update_dict: Dict[str, Any], participant_id: int) -> MissionJIAParticipant:
    """
    Update a mission participant.

    Args:
        user: User performing the update.
        update_dict: Dictionary of fields to update.
        participant_id: ID of the participant to update.
    """
    participant = mission_participant_details(participant_id)
    original_fields = {
        key: getattr(participant, key)
        for key in update_dict.keys()
        if hasattr(participant, key)
    }
    for key, value in update_dict.items():
        setattr(participant, key, value)
    changed_fields = []
    for key, old_value in original_fields.items():
        new_value = getattr(participant, key)
        if old_value != new_value:
            changed_fields.append(f"{key}: '{old_value}' → '{new_value}'")
    participant.save()
    if changed_fields:
        changes_text = ", ".join(changed_fields)
        log_description = (
            f"Updated mission participant '{participant.pk}:{participant.full_name}' "
            f"Changes: {changes_text}"
        )
        log_audit_event(
            user=user,
            action_category="missions",
            action_type=ActionType.MODIFICATION,
            action_description=log_description,
            is_successful=True
        )
    return participant


def delete_mission_participant(user, participant_id: int) -> MissionJIAParticipant:
    """
    Delete a mission participant.

    Args:
        user: User performing the deletion.
        participant_id: ID of the participant to delete.
    """
    participant = mission_participant_details(participant_id)
    participant.is_archived = True
    participant.save()
    log_audit_event(
        user=user,
        action_category="missions",
        action_type=ActionType.DELETION,
        action_description=f"Deleted mission participant '{participant.phone_number}:{participant.full_name}' from mission '{participant.mission.pk}:{participant.mission.title}'",
        is_successful=True
    )
    return participant


def bulk_create_mission_participants(participants_data: List[Dict[str, Any]]) -> List[MissionJIAParticipant]:
    """
    Bulk create mission participants.

    Args:
        participants_data: List of dictionaries containing participant data.
    """
    participants = []
    for data in participants_data:
        mission = mission_details(mission_id=data['mission_id'])
        user = None
        if 'user_id' in data and data['user_id']:
            user = user_details(user_id=data['user_id'])
        if not data.get('full_name') and user is None:
            raise CustomValidationError("Either full name or user id must be provided.")
        if not data.get('phone_number') and (user is None or user.phone_number is None):
            raise CustomValidationError("Phone number is a required field")
        participant = MissionJIAParticipant(
            mission=mission,
            user=user,
            full_name=data.get('full_name') or (user.get_full_name() if user else ''),
            phone_number=data.get('phone_number') or (user.phone_number if user else ''),
            travelling_from=data['travelling_from'],
            diet_advisory=data.get('diet_advisory', 'N/A'),
            days_of_attendance=data['days_of_attendance'],
            need_facilitation=data.get('need_facilitation', False),
            gender=data['gender']
        )
        participants.append(participant)
    MissionJIAParticipant.objects.bulk_create(participants)
    return participants


def delete_mission_participants_by_mission(mission_id: int, participant_ids: List[int]) -> int:
    """
    Delete all mission participants associated with a specific mission.

    Args:
        mission_id: ID of the mission whose participants are to be deleted.
        participant_ids: List of participant IDs to delete.

    Returns:
        The number of participants deleted.
    """
    participants = MissionJIAParticipant.objects.filter(mission__id=mission_id, ids__in=participant_ids, is_archived=False)
    count = participants.count()
    if count == 0:
        raise CustomValidationError("No participants found for the given mission and participant IDs.")
    participants.update(is_archived=True)
    return count


def create_report(
    mission_id: int,
    title: str,
    content: str,
    created_by_id: int,
    report_file: Optional[Any] = None
):
    mission = mission_details(mission_id=mission_id)
    created_by = user_details(user_id=created_by_id)
    report = Report.objects.create(
        mission=mission,
        title=title,
        content=content,
        created_by=created_by,
        report_file=report_file
    )
    log_audit_event(
        user=created_by,
        action_category="reports",
        action_type=ActionType.CREATION,
        action_description=f"{created_by.email} created report '{report.pk}:{report.title}' for mission '{mission.pk}:{mission.title}'",
        is_successful=True
    )
    return report


def update_report(user, update_dict: Dict[str, Any], report_id: int) -> Report:
    """
    Update a report.

    Args:
        user: User performing the update.
        update_dict: Dictionary of fields to update.
        report_id: ID of the report to update.
    """
    report = report_details(report_id)
    original_fields = {
        key: getattr(report, key)
        for key in update_dict.keys()
        if hasattr(report, key)
    }
    if 'mission_id' in update_dict:
        mission = mission_details(update_dict.pop('mission_id'))
        report.mission = mission

    for key, value in update_dict.items():
        setattr(report, key, value)
    changed_fields = []
    for key, old_value in original_fields.items():
        new_value = getattr(report, key)
        if old_value != new_value:
            changed_fields.append(f"{key}: '{old_value}' → '{new_value}'")
    if changed_fields:
        changes_text = ", ".join(changed_fields)
        log_description = (
            f"{user.email} updated report '{report.pk}:{report.title}' "
            f"Changes: {changes_text}"
        )
        log_audit_event(
            user=user,
            action_category="reports",
            action_type=ActionType.MODIFICATION,
            action_description=log_description,
            is_successful=True
        )
    report.save()
    return report


def delete_report(user, report_id: int) -> Report:
    """
    Delete a report.

    Args:
        user: User performing the deletion.
        report_id: ID of the report to delete.
    """
    report = report_details(report_id)
    report.is_archived = True
    log_message = f"{user.email} deleted report '{report.pk}:{report.title}' for mission '{report.mission.pk}:{report.mission.title}'"
    report.save()
    log_audit_event(
        user=user,
        action_category="reports",
        action_type=ActionType.DELETION,
        action_description=log_message,
        is_successful=True
    )
    return report


def bulk_create_gallery_images(mission_id: int, uploaded_by_id: int, images_data: List[Dict[str, Any]]) -> List:
    """
    Bulk create mission gallery images.

    Args:
        mission_id: ID of the mission to which images are to be added.
        uploaded_by_id: ID of the user uploading the images.
        images_data: List of dictionaries containing image data.
    """
    images = []
    for data in images_data:
        mission = mission_details(mission_id=mission_id)
        uploaded_by = user_details(user_id=uploaded_by_id)
        image = MissionGallery(
            mission=mission,
            title=data.get('title', ''),
            image=data['image'],
            description=data.get('description', ''),
            uploaded_by=uploaded_by
        )
        images.append(image)
    MissionGallery.objects.bulk_create(images)
    return images


def bulk_delete_gallery_images_by_mission(user, mission_id: int, image_ids: List[int]) -> int:
    """
    Bulk delete all gallery images associated with a specific mission.

    Args:
        user: User performing the deletion.
        mission_id: ID of the mission whose gallery images are to be deleted.
        image_ids: List of image IDs to delete.

    Returns:
        The number of gallery images deleted.
    """
    images = MissionGallery.objects.filter(mission__id=mission_id, id__in=image_ids)
    count = images.count()
    images.delete()
    log_audit_event(
        user=user,
        action_category="missions",
        action_type=ActionType.DELETION,
        action_description=f"{user.email} deleted {count} gallery images from mission ID {mission_id}",
        is_successful=True
    )
    return count
