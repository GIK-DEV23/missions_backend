import datetime
import decimal
import uuid
from decimal import Decimal
from enum import Enum
from typing import Union, Optional, Any, Type, Callable

from django.db import models
from django.utils import timezone

from base.utils.exceptions import CustomValidationError


def commas(value: Union[Decimal, int, float], use_decimal: bool = False) -> str:
    return "{:,.2f}".format(value) if use_decimal else "{:,}".format(value)


def format_phone_number(phone_number):
    phone_number = str(phone_number)
    if len(phone_number) < 9:
        raise CustomValidationError("Invalid Phone Number")
    phone = phone_number[-9:]
    return "+254{}".format(phone)


def apply_sorting(
    qs: models.QuerySet,
    sort_by: str = "created_at",
    is_desc: bool = True,
    allowed_fields: Optional[list[str]] = None
) -> models.QuerySet:
    """
    Apply dynamic sorting to a queryset, with safe field validation.
    """
    if not allowed_fields:
        allowed_fields = ["created_at"]

    # Fallback to created_at if not allowed
    print(sort_by, allowed_fields)
    if sort_by not in allowed_fields:
        sort_by = "created_at"

    prefix = "-" if is_desc else ""
    print(prefix + sort_by)
    return qs.order_by(f"{prefix}{sort_by}")


def serialize_types(
    data: Any,
    type_serializers: dict[Type, Callable[[Any], Any]] | None = None,
    readable: bool = True,
) -> Any:
    """
    Recursively serialize specified types within nested data structures,
    with optional readable formatting for time and date values.

    Args:
        data: The data (dict, list, or primitive) to process.
        type_serializers: A dictionary mapping types to serializer functions.
        readable: If True, use human-friendly formats for time/date types.

    Returns:
        The same structure with all matching types converted.
    """

    if type_serializers is None:
        def serialize_date(v: datetime.date):
            return v.strftime("%A, %d %B %Y") if readable else v.isoformat()

        def serialize_time(v: datetime.time):
            return v.strftime("%I:%M %p") if readable else v.isoformat()

        def serialize_datetime(v: datetime.datetime):
            return v.strftime("%A, %d %B %Y %I:%M %p") if readable else v.isoformat()

        type_serializers = {
            datetime.date: serialize_date,
            datetime.datetime: serialize_datetime,
            datetime.time: serialize_time,
            decimal.Decimal: str,
            uuid.UUID: str,
            Enum: lambda v: v.value,
        }

    # Handle lists
    if isinstance(data, list):
        return [serialize_types(item, type_serializers, readable) for item in data]

    # Handle dicts
    if isinstance(data, dict):
        return {
            key: serialize_types(value, type_serializers, readable)
            for key, value in data.items()
        }

    # Handle direct type match
    for t, serializer in type_serializers.items():
        if isinstance(data, t):
            return serializer(data)

    return data


def resolve_fk_by_client_id(data: dict, field: str, model: Type[models.Model]) -> dict:
    """
    Resolve '{field}_client_id' to '{field}_id' in-place when the numeric id
    wasn't given, for FKs to records that may only exist offline so far.
    """
    id_key = f"{field}_id"
    client_key = f"{field}_client_id"
    client_id = data.pop(client_key, None)
    if data.get(id_key) is None and client_id:
        try:
            data[id_key] = model.objects.only("id").get(client_id=client_id).id
        except model.DoesNotExist:
            raise CustomValidationError(
                "No {} found for client_id '{}'".format(model.__name__.lower(), client_id)
            )
    return data


def validate_date(value, row):
    """
    Validate and normalize a date value.
    Returns a Python date object if valid, otherwise raises an error.
    """
    if not value:
        return None

    # Already a datetime object (Excel files often do this)
    if isinstance(value, datetime.datetime):
        return value.date()

    # Try to parse string values in common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed = datetime.datetime.strptime(str(value).strip(), fmt)
            return parsed.date()
        except ValueError:
            continue

    raise CustomValidationError(
        "Invalid date format '{}' in row {}. Expected formats: YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY.".format(value, row)
    )
