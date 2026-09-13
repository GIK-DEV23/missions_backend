from enum import Enum
from typing import Optional, List

from ninja import Schema

from base.schemas import BaseOut, BaseQuery
from users.constants import GenderType


class UserType(str, Enum):
    ADMIN = 'admin'
    MISSIONER = 'missioner'
    STAFF = 'staff'
    EXEC = 'exec'


class TimeFilter(str, Enum):
    LIFETIME = 'lifetime'
    THIS_YEAR = 'this_year'
    LAST_YEAR = 'last_year'
    LAST_6_MONTHS = 'last_6_months'
    LAST_3_MONTHS = 'last_3_months'
    LAST_MONTH = 'last_month'


class MeStatsQuery(Schema):
    time_filter: Optional[TimeFilter] = TimeFilter.LIFETIME


class MeStatsOut(Schema):
    checks_in_this_week: int
    souls_won: int
    in_follow_up: int
    missions_count: int
    souls_with_data_count: int
    souls_without_consent_count: int


class RoleQuery(BaseQuery):
    name: Optional[str] = None


class RoleSchema(BaseOut):
    name: str
    description: str
    permissions: list[str]


class UserFilterSchema(BaseQuery):
    search: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UserCreate(Schema):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    password: str
    profile_photo: str | None = None
    preferred_username: str | None = None
    role_id: int | None = None
    permissions: list[str] | None = None
    role_name: str | None = None
    user_type: Optional[UserType] = None


class RoleCreate(Schema):
    name: str
    description: Optional[str] = ''
    permissions: list[str]


class RoleOut(Schema):
    id: int
    name: str
    description: str
    permissions: list[str]


class PermissionQuery(Schema):
    user_type: Optional[UserType] = None


class SavedPartner(Schema):
    name: str
    gender: GenderType
    traveling_from: str
    dietary: str


class UserProfileOut(BaseOut):
    """Self-serve profile — fuller than UserData, only ever returned to the owning user."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: str
    phone_number: Optional[str] = None
    church: Optional[str] = None
    bio: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_confirmed_at: Optional[str] = None
    saved_partner: Optional[SavedPartner] = None
    profile_photo: Optional[str] = None
    roles: List[str] = []


class UserProfileUpdate(Schema):
    phone_number: Optional[str] = None
    church: Optional[str] = None
    bio: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    saved_partner: Optional[SavedPartner] = None
