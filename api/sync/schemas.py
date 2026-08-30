import datetime
import uuid
from typing import Optional, List

from ninja import Schema


class MutationIn(Schema):
    client_mutation_id: str
    entity: str
    client_id: uuid.UUID
    op: str
    payload: dict = {}


class MutationsIn(Schema):
    mutations: List[MutationIn]


class MutationResultOut(Schema):
    client_mutation_id: str
    status: str
    id: Optional[int] = None
    client_id: Optional[str] = None
    error: Optional[str] = None


class MutationsOut(Schema):
    results: List[MutationResultOut]


class ChangesQuery(Schema):
    since: Optional[datetime.datetime] = None
