import datetime
import uuid
from typing import Optional

from ninja import Schema

from base.schemas import BaseOut
from personal_missions.constants import PersonalMissionType, PersonalMissionRhythm


class PersonalMissionCreate(Schema):
    client_id: Optional[uuid.UUID] = None
    name: str
    type: PersonalMissionType
    start_date: datetime.date
    end_date: Optional[datetime.date] = None
    rhythm: PersonalMissionRhythm = PersonalMissionRhythm.NONE
    rhythm_day: Optional[int] = None
    location: Optional[str] = None
    reminder_enabled: bool = False
    reminder_time: Optional[datetime.time] = None
    what_happened: Optional[str] = None


class PersonalMissionUpdate(Schema):
    name: Optional[str] = None
    type: Optional[PersonalMissionType] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    rhythm: Optional[PersonalMissionRhythm] = None
    rhythm_day: Optional[int] = None
    location: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    reminder_time: Optional[datetime.time] = None
    what_happened: Optional[str] = None


class PersonalMissionOut(BaseOut):
    client_id: Optional[str] = None
    owner_id: int
    name: str
    type: str
    start_date: datetime.date
    end_date: Optional[datetime.date] = None
    rhythm: str
    rhythm_day: Optional[int] = None
    location: Optional[str] = None
    reminder_enabled: bool
    reminder_time: Optional[datetime.time] = None
    archived_at: Optional[str] = None
    what_happened: Optional[str] = None
