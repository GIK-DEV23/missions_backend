"""
1. Create soul
2. Update soul
3. Delete soul
4. Create progress update
5. Update progress update
6. Delete progress update
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit_logs.constants import ActionType
from audit_logs.services import log_audit_event
from base.utils.exceptions import CustomValidationError, handle_cleaning_error
from base.utils.file_parser import FileParser
from base.utils.helpers import validate_date, resolve_fk_by_client_id
from missions.selectors import location_details, mission_details
from souls.models import Soul, ProgressUpdate
from souls.selectors import get_soul, get_soul_by_client_id
from users.constants import GenderType, AgeGroupCategory
from users.models import User
from users.selectors import user_details


def create_soul(data) -> Soul:
    try:
        location_id = data.get("location")
        user_id = data.get("user")
        mission_id = data.get("mission")
        if location_id is not None:
            location = location_details(location_id)
            data["location"] = location
        if user_id is not None:
            user = user_details(user_id)
            data["user"] = user
        if mission_id is not None:
            mission = mission_details(mission_id)
            data["mission"] = mission
        soul = Soul(**data)
        soul.full_clean()
        soul.save()
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("Error creating soul: {}".format(e))
    return soul


def update_soul(user, soul_id, data) -> Soul:
    try:
        soul = get_soul(soul_id)
        new_contact_outcome = data.get("contact_outcome")
        if soul.contact_outcome and new_contact_outcome and new_contact_outcome != soul.contact_outcome:
            raise CustomValidationError("contact_outcome is immutable once set")
        original_fields = {field: getattr(soul, field) for field in data.keys()}
        for key, value in data.items():
            if value is not None:
                if key == "location":
                    location = location_details(value)
                    setattr(soul, key, location)
                if key == "mission":
                    mission = mission_details(value)
                    setattr(soul, key, mission)
                setattr(soul, key, value)
        soul.full_clean()
        changed_fields = {field: (original_fields[field], getattr(soul, field)) for field in data.keys() if original_fields[field] != getattr(soul, field)}
        soul.save()
        if changed_fields:
            changed_fields_str = ", ".join(f"{field}: '{original}' -> '{new}'" for field, (original, new) in changed_fields.items())
            log_message = f"Soul ID {soul_id} updated. Changes: {changed_fields_str}"
            log_audit_event(
                user=user,
                action_type=ActionType.MODIFICATION,
                action_category="souls",
                action_description=log_message,
                is_successful=True
            )
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("Error updating soul: {}".format(e))
    return soul


def delete_soul(user, soul_id) -> Soul:
    soul = get_soul(soul_id)
    try:
        soul.delete()
        log_audit_event(
            user=user,
            action_type=ActionType.DELETION,
            action_category="souls",
            action_description=f"Soul ID {soul_id} deleted.",
            is_successful=True
        )
        return soul
    except Exception as e:
        raise CustomValidationError("Error deleting soul: {}".format(e))


def create_progress_update(data: dict) -> ProgressUpdate:
    data = resolve_fk_by_client_id(data, "soul", Soul)
    soul_id = data.pop("soul_id", None)
    if not soul_id:
        raise CustomValidationError("Either soul_id or soul_client_id is required")
    soul = get_soul(soul_id)
    author_id = data.pop("author_id", None)
    if author_id is not None:
        data["author"] = user_details(author_id)
    next_check_in_at = data.get("next_check_in_at")
    try:
        progress_update = ProgressUpdate(soul=soul, **data)
        progress_update.full_clean()
        progress_update.save()
        soul_update_fields = ["last_contacted_at"]
        soul.last_contacted_at = progress_update.created_at
        if next_check_in_at:
            soul.next_check_in_at = next_check_in_at
            soul_update_fields.append("next_check_in_at")
        soul.save(update_fields=soul_update_fields)
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("Error creating progress update: {}".format(e))
    return progress_update


def update_progress_update(progress_update_id: int, data: dict) -> ProgressUpdate:
    try:
        data = resolve_fk_by_client_id(data, "soul", Soul)
        progress_update = ProgressUpdate.objects.get(id=progress_update_id)
        author_id = data.pop("author_id", None)
        if author_id is not None:
            data["author"] = user_details(author_id)
        next_check_in_at = data.get("next_check_in_at")
        for key, value in data.items():
            if value is not None:
                setattr(progress_update, key, value)
        progress_update.full_clean()
        progress_update.save()
        if next_check_in_at:
            progress_update.soul.next_check_in_at = next_check_in_at
            progress_update.soul.save(update_fields=["next_check_in_at"])
    except ProgressUpdate.DoesNotExist:
        raise CustomValidationError(f"Progress update with ID {progress_update_id} does not exist")
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("Error updating progress update: {}".format(e))
    return progress_update


def delete_progress_update(progress_update_id: int) -> ProgressUpdate:
    try:
        progress_update = ProgressUpdate.objects.get(id=progress_update_id)
        soul = progress_update.soul
        progress_update.delete()
        latest = soul.progress_updates.order_by("-created_at").first()
        soul.last_contacted_at = latest.created_at if latest else None
        soul.save(update_fields=["last_contacted_at"])
        return progress_update
    except ProgressUpdate.DoesNotExist:
        raise CustomValidationError(f"Progress update with ID {progress_update_id} does not exist")
    except Exception as e:
        raise CustomValidationError("Error deleting progress update: {}".format(e))


def validate_gender(value, row):
    valid_values = [v.lower() for v in GenderType.values]
    if value is not None and str(value).strip().lower() not in valid_values:
        raise CustomValidationError(
            "Invalid gender '{}' in row {}. Allowed: {}".format(
                value, row, ", ".join(GenderType.values)
            )
        )


def validate_age_group(value, row):
    valid_values = [v.lower() for v in AgeGroupCategory.values]
    if value is not None and str(value).strip().lower() not in valid_values:
        raise CustomValidationError(
            "Invalid age group '{}' in row {}. Allowed: {}".format(
                value, row, ", ".join(AgeGroupCategory.values)
            )
        )


def upload_souls(user, file, mission_id: int, location_id: int):
    try:
        mission = mission_details(mission_id)
        location = location_details(location_id)

        mandatory_fields = [
            "missioner_email", "first_name", "last_name", "phone_number", "gender", "age_group", "description"
        ]

        readable_map = {
            "missioner_email": "Missioner Email",
            "first_name": "First Name",
            "last_name": "Last Name",
            "phone_number": "Phone Number",
            "gender": "Gender",
            "age_group": "Age Group",
            "description": "Description",
            "date_added": "Date Added",
        }

        field_validators = {
            "gender": validate_gender,
            "age_group": validate_age_group,
            "date_added": validate_date,
        }

        parser = FileParser(
            file,
            mandatory_fields=mandatory_fields,
            readable_field_map=readable_map,
            field_validators=field_validators,
        )

        parsed_data = parser.to_dict()

        emails = {row["missioner_email"] for row in parsed_data if row["missioner_email"]}
        users = User.objects.filter(email__in=emails)
        user_map = {u.email: u for u in users}

        souls_to_create = []

        for row in parsed_data:
            user = user_map.get(row["missioner_email"])
            if not user:
                raise CustomValidationError(f"No registered user found with email '{row['missioner_email']}'")

            soul = Soul(
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                phone_number=row["phone_number"].strip(),
                gender=row["gender"].lower().strip(),
                age_group=row["age_group"].strip(),
                description=row["description"].strip(),
                mission=mission,
                location=location,
                user=user,
                date_added=row.get("date_added") or timezone.now().date(),
                uploaded_at=timezone.now(),
            )
            souls_to_create.append(soul)

        with transaction.atomic():
            Soul.objects.bulk_create(souls_to_create, batch_size=1000)
        log_audit_event(
            user=user,
            action_type=ActionType.CREATION,
            action_category="souls",
            action_description=f"Uploaded {len(souls_to_create)} souls via file upload.",
            is_successful=True
        )
        return {"message": f"{len(souls_to_create)} souls successfully uploaded."}
    except CustomValidationError as e:
        raise e
    except Exception as e:
        raise CustomValidationError("Error uploading souls: {}".format(e))



def progress_update_handler(user, kwargs):
    progress_update_in = kwargs.get("progress_update_in")
    soul_id = progress_update_in.soul_id if progress_update_in else kwargs.get("soul_id")
    soul_client_id = progress_update_in.soul_client_id if progress_update_in else None
    if soul_id:
        soul = get_soul(soul_id)
    elif soul_client_id:
        soul = get_soul_by_client_id(soul_client_id)
    else:
        return None
    if not soul.user or soul.user.pk != user.pk:
        raise CustomValidationError("You can only view/write/edit/delete notes for souls assigned to you.")
    return None


def missioner_soul_operations_handler(user, kwargs):
    """
    Restriction handler for missioners updating souls.
    Ensures missioners can only update souls associated to them.
    """
    print("KWARGS", kwargs)
    soul_id = kwargs.get('soul_id')
    if not soul_id:
        raise CustomValidationError("Soul ID is required.")

    soul = get_soul(soul_id=soul_id)

    if not soul.user or soul.user.pk != user.id:
        raise CustomValidationError("You can only view/update souls assigned to you.")
