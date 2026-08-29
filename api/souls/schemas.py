import datetime
import uuid
from enum import Enum
from typing import Optional

from ninja import Schema

from base.schemas import BaseQuery, FilterQuery, BaseOut
from souls.constants import JourneyStage, ContactOutcome, ProgressUpdateType, ProgressUpdateOutcome
from users.constants import GenderType, AgeGroupCategory


class AgeGroupEnum(str, Enum):
    CHILD = '0-12'
    TEEN = '13-17'
    YOUNG_ADULT = '18-24'
    ADULT = '25-39'
    MATURE_ADULT = '40-59'
    SENIOR = '60+'


class SoulsListByEnum(str, Enum):
    UPLOADED_AT = 'uploaded_at'
    FIRST_NAME = 'first_name'
    PHONE_NUMBER = 'phone_number'
    DATE_ADDED = 'date_added'


class SoulsQuery(BaseQuery):
    """Schema for querying souls with pagination."""
    is_personal: Optional[bool] = None
    mission: Optional[int] = None
    gender: Optional[GenderType] = None
    age_group: Optional[AgeGroupCategory] = None
    location: Optional[int] = None
    status: Optional[JourneyStage] = None
    search: Optional[str] = None
    created_before: Optional[datetime.date] = None
    created_after: Optional[datetime.date] = None
    user: Optional[int] = None
    sort_by: Optional[SoulsListByEnum] = None
    is_desc: Optional[bool] = True


class SoulCreate(Schema):
    """Schema for creating a soul."""
    client_id: Optional[uuid.UUID] = None
    first_name: str
    last_name: str
    phone_number: str
    gender: GenderType
    age_group: AgeGroupCategory
    location: Optional[int] = None
    status: JourneyStage
    contact_outcome: Optional[ContactOutcome] = None
    date_added: Optional[datetime.date] = None
    mission: Optional[int] = None
    is_personal: bool = False
    user: Optional[int] = None
    description: Optional[str] = None


class SoulUpdate(Schema):
    """Schema for updating a soul."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    age_group: Optional[AgeGroupCategory] = None
    location: Optional[int] = None
    status: Optional[JourneyStage] = None
    contact_outcome: Optional[ContactOutcome] = None
    date_added: Optional[datetime.date] = None
    mission: Optional[int] = None
    is_personal: bool = False
    user: Optional[int] = None
    description: Optional[str] = None

class ProgressUpdateSummary(BaseOut):
    """Schema for progress update output."""
    content: str
    update_date: datetime.date


class SoulUploadIn(Schema):
    mission_id: int
    location_id: int


class SoulOut(BaseOut):
    """Schema for soul output."""
    client_id: Optional[str] = None
    first_name: str
    last_name: str
    phone_number: str
    gender: str
    age_group: str
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    status: str
    contact_outcome: Optional[str] = None
    date_added: datetime.date
    mission_id: Optional[int] = None
    mission_title: Optional[str] = None
    is_personal: bool = False
    user_id: Optional[int] = None
    user_full_name: Optional[str] = None
    soul_full_name: str
    description: Optional[str] = None
    next_check_in_at: Optional[str] = None
    last_contacted_at: Optional[str] = None


class SoulDetailsOut(SoulOut):
    """Schema for detailed soul output."""
    latest_progress_update: Optional[ProgressUpdateSummary] = None
    initial_progress_update: Optional[ProgressUpdateSummary] = None


class ProgressUpdateCreate(Schema):
    """Schema for creating a progress update."""
    client_id: Optional[uuid.UUID] = None
    soul_id: Optional[int] = None
    soul_client_id: Optional[uuid.UUID] = None
    author_id: Optional[int] = None
    content: str
    update_date: Optional[datetime.date] = None
    type: Optional[ProgressUpdateType] = None
    outcome: Optional[ProgressUpdateOutcome] = None
    next_check_in_at: Optional[datetime.datetime] = None


class ProgressUpdateOut(BaseOut):
    """Schema for progress update output."""
    client_id: Optional[str] = None
    soul_id: int
    author_id: Optional[int] = None
    author_full_name: Optional[str] = None
    content: str
    update_date: datetime.date
    type: Optional[str] = None
    outcome: Optional[str] = None
    next_check_in_at: Optional[str] = None
    soul_full_name: Optional[str] = None


class ProgressUpdateQuery(BaseQuery):
    """Schema for querying progress updates with pagination."""
    soul_id: Optional[int] = None
    is_desc: Optional[bool] = True
