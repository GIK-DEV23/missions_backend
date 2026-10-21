import datetime
import uuid
from typing import List, Optional

from ninja import Schema

from base.schemas import BaseOut, BaseQuery
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


class AllPersonalMissionsQuery(BaseQuery):
    """Filters for the organisation-wide admin list (BR-2).

    `user` is the owner's id. Named `user` rather than `owner_id` to match the
    filter key the souls list already uses for the same concept.
    """

    user: Optional[int] = None
    type: Optional[PersonalMissionType] = None
    rhythm: Optional[PersonalMissionRhythm] = None
    include_archived: bool = False


# ─── Session Schemas ───────────────────────────────────────────────────────────

class SessionCreate(Schema):
    date: datetime.date
    notes: Optional[str] = None
    souls_count: int = 0
    duration_minutes: Optional[int] = None


class SessionOut(BaseOut):
    mission_id: int
    date: datetime.date
    notes: Optional[str] = None
    souls_count: int
    duration_minutes: Optional[int] = None


# ─── Rhythm Period Schemas ─────────────────────────────────────────────────────

class RhythmPeriodOut(Schema):
    """A single period in the rhythm timeline."""
    index: int
    start: datetime.date
    end: datetime.date
    met: bool
    met_at: Optional[str] = None  # ISO datetime string


# ─── Personal Mission Output with Rhythm ───────────────────────────────────────

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
    # Rhythm tracking fields (computed)
    rhythm_periods: List[RhythmPeriodOut] = []
    met_count: int = 0
    current_period_index: Optional[int] = None
