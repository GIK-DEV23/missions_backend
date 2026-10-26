from typing import Optional

from ninja import Router, Schema

from authentication.permissions import jwt_auth
from base.schemas import DetailOut
from users.constants import GenderType
from users.models import User
from users.schemas import SavedPartner
from users.services import update_registration_defaults

router = Router(tags=["registration-defaults"])


class RegistrationDefaultsOut(Schema):
    full_name: str
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    travelling_from: Optional[str] = None
    diet_advisory: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    saved_partner: Optional[SavedPartner] = None


class RegistrationDefaultsUpdate(Schema):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    travelling_from: Optional[str] = None
    diet_advisory: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    saved_partner: Optional[SavedPartner] = None


def _serialize_defaults(user: User) -> dict:
    return {
        "full_name": user.get_full_name(),
        "phone_number": str(user.phone_number) if user.phone_number else None,
        "gender": user.gender,
        "travelling_from": user.travelling_from,
        "diet_advisory": user.diet_advisory,
        "emergency_contact_name": user.emergency_contact_name,
        "emergency_contact_phone": str(user.emergency_contact_phone) if user.emergency_contact_phone else None,
        "saved_partner": user.saved_partner,
    }


@router.get(
    "/registration-defaults/",
    response={200: RegistrationDefaultsOut},
    auth=jwt_auth,
)
def get_registration_defaults_api(request):
    return 200, RegistrationDefaultsOut(**_serialize_defaults(request.user))


@router.put(
    "/registration-defaults/",
    response={200: RegistrationDefaultsOut, 400: DetailOut},
    auth=jwt_auth,
)
def update_registration_defaults_api(request, defaults_in: RegistrationDefaultsUpdate):
    user = update_registration_defaults(request.user, defaults_in.dict(exclude_unset=True))
    return 200, RegistrationDefaultsOut(**_serialize_defaults(user))
