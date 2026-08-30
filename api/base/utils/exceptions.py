import re
from typing import Any, Dict, List, Union

from django.db.utils import IntegrityError
from ninja.errors import ValidationError


class CustomValidationError(ValidationError):
    def __init__(self, errors: Union[str, List[Dict[str, Any]]]) -> None:
        self.errors = errors  # type: ignore
        super().__init__(errors)  # type: ignore


def parse_integrity_error(error: IntegrityError) -> str:
    message = str(error)

    # Check for unique constraint violation
    if "duplicate key value violates unique constraint" in message:
        match = re.search(r"Key \(([\w, ]+)\)=\((.*?)\) already exists", message)
        if match:
            fields, value = match.groups()
            field_names = [f.strip() for f in fields.split(",")]
            if len(field_names) == 1:
                return "The value '{}' is already used for '{}'. Please use a different one.".format(value, field_names[0])
            return "A record with this combination of {} already exists.".format(", ".join(field_names))
        else:
            return "A unique constraint was violated. Please check your input values."

    # Add more patterns here if needed
    return "A database error occurred. Please try again or contact support."


def handle_cleaning_error(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        errors = []
        for field, messages in error.message_dict.items():
            for msg in messages:
                errors.append(f"{field}: {msg}")
        return "; ".join(errors)
    elif hasattr(error, "messages"):
        return "; ".join(error.messages)
    else:
        return str(error)