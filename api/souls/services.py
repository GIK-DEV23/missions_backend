"""
1. Create soul
2. Update soul
3. Delete soul
4. Create progress update
5. Update progress update
6. Delete progress update
"""
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from ninja.errors import HttpError

from audit_logs.constants import ActionType
from audit_logs.services import log_audit_event
from base.utils.exceptions import CustomValidationError, ForbiddenError, handle_cleaning_error
from base.utils.file_parser import FileParser
from base.utils.helpers import validate_date, resolve_fk_by_client_id, normalize_kenyan_phone
from missions.selectors import location_details, mission_details
from personal_missions.models import PersonalMission
from personal_missions.selectors import personal_mission_details
from souls.models import Soul, ProgressUpdate
from souls.selectors import get_soul, get_soul_by_client_id
from users.constants import GenderType, AgeGroupCategory
from users.models import User
from users.selectors import user_details

FK_RESOLVERS = {
    "location": location_details,
    "mission": mission_details,
    "personal_mission": personal_mission_details,
    "user": user_details,
}


def _resolve_personal_mission(user, data: dict):
    """Resolve `personal_mission` FK from either an int id or a client UUID.

    Pops `personal_mission_client_id` from *data* (never stored on the model
    directly).  Rules:
    - `personal_mission` (int) present → use directly, skip UUID lookup.
    - `personal_mission_client_id` (UUID) present, no int → look up by
      (owner, client_id).  Found → set `personal_mission`; not found → 409
      so the client retries after the mission syncs.
    - Neither present → no-op.
    """
    client_id = data.pop("personal_mission_client_id", None)

    # If the int FK is already present, it wins; UUID is only a fallback.
    if data.get("personal_mission") is not None:
        if client_id is not None:
            import logging
            logging.getLogger(__name__).warning(
                "Soul create/update: both personal_mission (int) and "
                "personal_mission_client_id supplied; using int."
            )
        return  # FK_RESOLVERS will handle the int lookup as usual

    if client_id is None:
        return  # no mission link requested

    try:
        pm = PersonalMission.objects.get(client_id=client_id, owner=user)
        data["personal_mission"] = pm.id
    except PersonalMission.DoesNotExist:
        raise HttpError(
            409,
            {
                "code": "MISSION_NOT_SYNCED",
                "detail": (
                    "Personal mission with client_id={} not found on server yet. "
                    "Sync the mission first, then retry."
                ).format(client_id),
            },
        )


def _find_possible_duplicate(phone_number, exclude_id=None) -> Optional[int]:
    qs = Soul.objects.filter(phone_number=phone_number, deleted_at__isnull=True)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    match = qs.order_by("created_at").first()
    return match.id if match else None


def _stamp_consent_and_contact_fields(data: dict, existing_consent_recorded_at=None, existing_do_not_contact_at=None):
    if data.get("consent_given") and not data.get("consent_recorded_at") and not existing_consent_recorded_at:
        data["consent_recorded_at"] = timezone.now()
    if data.get("do_not_contact") and not data.get("do_not_contact_at") and not existing_do_not_contact_at:
        data["do_not_contact_at"] = timezone.now()
    # Auto-stamp guardian_consent_date when guardian_consent_given flips to True
    if data.get("guardian_consent_given") and not data.get("guardian_consent_date"):
        data["guardian_consent_date"] = timezone.now()


# Age groups that require guardian consent (minors: 0-12 and 13-17)
MINOR_AGE_GROUPS = {AgeGroupCategory.CHILD, AgeGroupCategory.YOUNG_TEEN}


def _validate_guardian_consent_for_minor(data: dict, existing_soul=None):
    """
    Validate guardian consent fields for minors per BR-4.

    For minors (age_group in {0-12, 13-17}), consent_given can only be accepted
    as True when guardian_name, guardian_relationship, and guardian_consent_given
    are all set.

    On create: check data.
    On update: merge data with existing soul fields.
    """
    # Determine the effective age_group (from data or existing soul)
    age_group = data.get("age_group")
    if age_group is None and existing_soul:
        age_group = existing_soul.age_group
    if age_group is None:
        return  # Cannot validate without an age group

    # Check if this is a minor
    is_minor = age_group in MINOR_AGE_GROUPS or age_group in {ag.value for ag in MINOR_AGE_GROUPS}
    if not is_minor:
        return  # Not a minor, no guardian consent required

    # Determine effective consent_given
    consent_given = data.get("consent_given")
    if consent_given is None and existing_soul:
        consent_given = existing_soul.consent_given

    if not consent_given:
        return  # consent_given is False/None, validation passes (no claim of consent)

    # consent_given is True for a minor -- require guardian fields
    guardian_name = data.get("guardian_name")
    if guardian_name is None and existing_soul:
        guardian_name = existing_soul.guardian_name

    guardian_relationship = data.get("guardian_relationship")
    if guardian_relationship is None and existing_soul:
        guardian_relationship = existing_soul.guardian_relationship

    guardian_consent_given = data.get("guardian_consent_given")
    if guardian_consent_given is None and existing_soul:
        guardian_consent_given = existing_soul.guardian_consent_given

    missing = []
    if not guardian_name:
        missing.append("guardian_name")
    if not guardian_relationship:
        missing.append("guardian_relationship")
    if not guardian_consent_given:
        missing.append("guardian_consent_given")

    if missing:
        raise CustomValidationError(
            "For minors (age 0-17), consent_given requires guardian information: {}".format(", ".join(missing))
        )


def _split_full_name(full_name: str) -> tuple[str, str]:
    """Split a single full name into (first_name, last_name).

    The first whitespace-separated token is the first name; the remainder is
    the last name. A single-word name is allowed — the last name is left blank.
    Only a completely empty name is rejected.
    """
    parts = (full_name or "").strip().split()
    if not parts:
        raise CustomValidationError("full_name: Please enter a name.")
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def create_soul(user, data) -> Soul:
    try:
        # Idempotency: if a soul with this client_id already exists, return it.
        client_id = data.get("client_id")
        if client_id is not None:
            existing = Soul.objects.filter(client_id=client_id, deleted_at__isnull=True).first()
            if existing is not None:
                return existing

        # Accept a single full_name and split it into the model's first/last.
        if "full_name" in data:
            first_name, last_name = _split_full_name(data.pop("full_name"))
            data["first_name"] = first_name
            data["last_name"] = last_name
        # Normalize the phone to canonical E.164 (+254…), accepting the common
        # local formats (07…, 01…, 254…, +254…).
        if data.get("phone_number"):
            data["phone_number"] = normalize_kenyan_phone(data["phone_number"])
        # Resolve personal_mission_client_id → personal_mission int FK before
        # the generic FK_RESOLVERS loop runs (which expects ints).
        _resolve_personal_mission(user, data)
        for key, resolver in FK_RESOLVERS.items():
            if data.get(key) is not None:
                data[key] = resolver(data[key])
        _stamp_consent_and_contact_fields(data)
        _validate_guardian_consent_for_minor(data)
        if data.get("phone_number"):
            data["possible_duplicate_of_id"] = _find_possible_duplicate(data["phone_number"])
        
        with transaction.atomic():
            soul = Soul(**data)
            soul.full_clean()
            soul.save()
            
            # Mark rhythm period as met if soul is linked to a personal mission
            if soul.personal_mission:
                from personal_missions.services import mark_period_met
                mark_period_met(soul.personal_mission, soul.date_added)
                
    except HttpError:
        raise
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except CustomValidationError:
        raise
    except Exception as e:
        raise CustomValidationError("Error creating soul: {}".format(e))
    return soul


def update_soul(user, soul_id, data) -> Soul:
    try:
        soul = get_soul(soul_id)
        new_contact_outcome = data.get("contact_outcome")
        if soul.contact_outcome and new_contact_outcome and new_contact_outcome != soul.contact_outcome:
            raise CustomValidationError("contact_outcome is immutable once set")
        _stamp_consent_and_contact_fields(data, soul.consent_recorded_at, soul.do_not_contact_at)
        _validate_guardian_consent_for_minor(data, existing_soul=soul)
        if data.get("phone_number"):
            data["possible_duplicate_of_id"] = _find_possible_duplicate(data["phone_number"], exclude_id=soul.id)
        # Resolve personal_mission_client_id → personal_mission int FK before
        # the generic FK_RESOLVERS loop runs.
        _resolve_personal_mission(user, data)
        original_fields = {field: getattr(soul, field) for field in data.keys()}
        for key, value in data.items():
            if value is not None:
                if key in FK_RESOLVERS:
                    value = FK_RESOLVERS[key](value)
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
    except HttpError:
        raise
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    except Exception as e:
        raise CustomValidationError("Error updating soul: {}".format(e))
    return soul


def merge_souls(user, soul_id: int, into_id: int) -> Soul:
    if soul_id == into_id:
        raise CustomValidationError("Cannot merge a soul into itself")
    duplicate = get_soul(soul_id)
    survivor = get_soul(into_id)
    try:
        with transaction.atomic():
            ProgressUpdate.objects.filter(soul=duplicate).update(soul=survivor)
            duplicate.testimonies.update(soul=survivor)
            duplicate.miracles.update(soul=survivor)
            duplicate.deleted_at = timezone.now()
            duplicate.save(update_fields=["deleted_at"])
            # Any soul (including the survivor) flagged as a duplicate of the
            # now-merged-away record should point at the survivor instead.
            Soul.objects.filter(possible_duplicate_of_id=duplicate.id).update(possible_duplicate_of=survivor)
            # A soul can't be its own possible duplicate — clear that edge case.
            Soul.objects.filter(id=survivor.id, possible_duplicate_of_id=survivor.id).update(possible_duplicate_of=None)
            survivor.refresh_from_db(fields=["possible_duplicate_of"])
        log_audit_event(
            user=user,
            action_type=ActionType.MODIFICATION,
            action_category="souls",
            action_description=f"Soul ID {soul_id} merged into Soul ID {into_id}.",
            is_successful=True
        )
    except Exception as e:
        raise CustomValidationError("Error merging souls: {}".format(e))
    return survivor


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
        with transaction.atomic():
            progress_update = ProgressUpdate(soul=soul, **data)
            progress_update.full_clean()
            progress_update.save()
            soul_update_fields = ["last_contacted_at"]
            soul.last_contacted_at = progress_update.created_at
            if next_check_in_at:
                soul.next_check_in_at = next_check_in_at
                soul_update_fields.append("next_check_in_at")
            soul.save(update_fields=soul_update_fields)
            
            # Mark rhythm period as met if soul belongs to a personal mission
            if soul.personal_mission:
                from personal_missions.services import mark_period_met
                mark_period_met(soul.personal_mission, progress_update.update_date)
                
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
        raise ForbiddenError("You can only view/write/edit/delete notes for souls assigned to you.")
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
        raise ForbiddenError("You can only view/update souls assigned to you.")


def create_soul_assignment(user, data: dict):
    from souls.models import SoulAssignment
    from souls.selectors import get_soul
    
    soul = get_soul(data["soul_id"])
    assignee = user_details(data["user_id"])
    
    try:
        assignment = SoulAssignment(
            soul=soul,
            user=assignee,
            assigned_by=user,
            notes=data.get("notes", "")
        )
        assignment.full_clean()
        assignment.save()
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    return assignment


def update_soul_assignment(assignment_id: int, data: dict):
    from souls.selectors import get_soul_assignment
    
    assignment = get_soul_assignment(assignment_id)
    
    try:
        for key, value in data.items():
            if value is not None:
                setattr(assignment, key, value)
        assignment.full_clean()
        assignment.save()
    except ValidationError as e:
        error_message = handle_cleaning_error(e)
        raise CustomValidationError(error_message)
    return assignment
