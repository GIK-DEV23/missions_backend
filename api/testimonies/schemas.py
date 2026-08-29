"""
Schemas for testimonies and miracles using Django Ninja (pydantic)
"""
import datetime
import uuid
from typing import Optional, List

from ninja import Schema
from pydantic import Field

from base.schemas import BaseQuery, BaseOut


class TestimonyCreateSchema(Schema):
    client_id: Optional[uuid.UUID] = None
    title: str
    content: str
    soul_id: Optional[int] = None
    soul_client_id: Optional[uuid.UUID] = None
    user_id: Optional[int] = None
    mission_id: Optional[int] = None


class TestimonyUpdateSchema(Schema):
    title: Optional[str] = None
    content: Optional[str] = None
    soul_id: Optional[int] = None
    user_id: Optional[int] = None
    mission_id: Optional[int] = None
    is_selected: Optional[bool] = None


class TestimonyOutSchema(BaseOut):
    client_id: Optional[str] = None
    title: str
    content: str
    soul_id: Optional[int] = None
    soul_full_name: Optional[str] = None
    user_id: Optional[int] = None
    user_full_name: Optional[str] = None
    mission_id: Optional[int] = None
    mission_title: Optional[str] = None
    photo_url: Optional[str] = None
    is_selected: bool = False


class TestimonyAndMiracleFilterSchema(BaseQuery):
    soul_id: Optional[int] = None
    user_id: Optional[int] = None
    mission_id: Optional[int] = None
    created_before: Optional[datetime.date] = None
    created_after: Optional[datetime.date] = None
    is_selected: Optional[bool] = None
    search: Optional[str] = None


class MiracleCreateSchema(Schema):
    client_id: Optional[uuid.UUID] = None
    title: str
    content: str
    soul_id: Optional[int] = None
    soul_client_id: Optional[uuid.UUID] = None
    user_id: Optional[int] = None
    mission_id: Optional[int] = None


class MiracleUpdateSchema(Schema):
    title: Optional[str] = None
    content: Optional[str] = None
    soul_id: Optional[int] = None
    user_id: Optional[int] = None
    mission_id: Optional[int] = None


class MiracleOutSchema(BaseOut):
    client_id: Optional[str] = None
    title: str
    content: str
    soul_id: Optional[int] = None
    soul_full_name: Optional[str] = None
    user_id: Optional[int] = None
    user_full_name: Optional[str] = None
    mission_id: Optional[int] = None
    mission_title: Optional[str] = None
    photo_url: Optional[str] = None
