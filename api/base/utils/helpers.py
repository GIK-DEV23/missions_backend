import datetime
import decimal
import re
import uuid
from decimal import Decimal
from enum import Enum
from typing import Union, Optional, Any, Type, Callable

from django.db import models
from django.utils import timezone

from base.utils.exceptions import CustomValidationError


def commas(value: Union[Decimal, int, float], use_decimal: bool = False) -> str:
    return "{:,.2f}".format(value) if use_decimal else "{:,}".format(value)


# ── Kenyan phone validation/normalization ──────────────────────────────────
# Mirrors the forgiving client-side rules (see boda-plus-web shared/utils/phone):
# a Kenyan mobile number is a `254` country code followed by a 9-digit
# subscriber number beginning with `7` or `1`. We accept the many ways people
# type the same number and reduce them to a single canonical E.164 form.
#
# Accepted inputs (separators like spaces, dashes, dots and parens are ignored):
#   +254712345678, 254712345678, 0712345678, 0112345678, 712345678,
#   00254712345678

_KENYA_SUBSCRIBER_RE = re.compile(r"^[17]\d{8}$")
_PHONE_SEPARATORS_RE = re.compile(r"[\s().-]")

KENYAN_PHONE_MESSAGE = (
    "Enter a valid Kenyan mobile number "
    "(e.g. 0712345678, 0112345678 or +254712345678)."
)


def to_kenyan_subscriber(raw) -> Optional[str]:
    """Reduce a phone string to its 9-digit Kenyan subscriber number
    (e.g. ``712345678``), or ``None`` if it cannot be interpreted as one."""
    if raw is None:
        return None
    value = _PHONE_SEPARATORS_RE.sub("", str(raw).strip())
    if not value:
        return None

    # International access prefix, e.g. 00254... -> +254...
    if value.startswith("00"):
        value = "+" + value[2:]

    if value.startswith("+254"):
        value = value[4:]
    elif value.startswith("254"):
        value = value[3:]
    elif value.startswith("0"):
        value = value[1:]

    return value if _KENYA_SUBSCRIBER_RE.match(value) else None


def is_valid_kenyan_phone(raw) -> bool:
    """True when ``raw`` can be understood as a valid Kenyan mobile number."""
    return to_kenyan_subscriber(raw) is not None


def normalize_kenyan_phone(raw) -> str:
    """Normalize any accepted Kenyan mobile format to canonical E.164
    (``+254712345678``). Raises [CustomValidationError] with the canonical
    message if the input is not a recognizable Kenyan number."""
    subscriber = to_kenyan_subscriber(raw)
    if subscriber is None:
        raise CustomValidationError(KENYAN_PHONE_MESSAGE)
    return "+254{}".format(subscriber)


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
    if sort_by not in allowed_fields:
        sort_by = "created_at"

    prefix = "-" if is_desc else ""
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
