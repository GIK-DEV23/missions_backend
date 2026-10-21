"""Moderation schemas.

Each Out schema is the server side of an interface the dashboard already
declares in `src/types/moderation.ts`. Field names and enum values match it
exactly so neither client needs a translation layer.

Enum-valued fields are typed with their TextChoices rather than `str`, so the
generated OpenAPI schema carries the allowed values (BR-5) and a client can
generate a real union instead of hand-retyping one.
"""

import datetime
import uuid
from typing import List, Optional

from ninja import Schema

from base.schemas import BaseOut, BaseQuery
from moderation.constants import (
    DeletionStatus,
    ReportableContentType,
    ReportReason,
    ReportStatus,
)


# ─── Nested objects ───────────────────────────────────────────────────────────

class ReporterOut(Schema):
    """Mirrors ContentReporter."""

    id: int
    name: str
    email: str


class ReviewerOut(Schema):
    id: int
    name: str


class ContentPreviewOut(Schema):
    """Mirrors ContentPreview. Every field optional: the target may be gone."""

    title: Optional[str] = None
    body_excerpt: Optional[str] = None
    author_name: Optional[str] = None
    author_id: Optional[int] = None
    created_at: Optional[str] = None
    exists: bool = True


# ─── Content reports ──────────────────────────────────────────────────────────

class ContentReportOut(BaseOut):
    """Mirrors ContentReport."""

    client_id: Optional[str] = None
    content_type: ReportableContentType
    content_id: int
    reporter: Optional[ReporterOut] = None
    reason: ReportReason
    details: str = ""
    status: ReportStatus
    reviewed_by: Optional[ReviewerOut] = None
    reviewed_at: Optional[str] = None
    resolution_notes: str = ""
    content_preview: Optional[ContentPreviewOut] = None


class ContentReportCreate(Schema):
    """Mirrors CreateReportRequest, plus client_id for offline sync."""

    client_id: Optional[uuid.UUID] = None
    content_type: ReportableContentType
    content_id: int
    reason: ReportReason
    details: Optional[str] = None


class ContentReportUpdate(Schema):
    """Mirrors UpdateReportRequest."""

    status: ReportStatus
    resolution_notes: Optional[str] = None


class ContentReportBulkUpdate(ContentReportUpdate):
    ids: List[int]


class BulkUpdateOut(Schema):
    updated: int
    skipped: List[int] = []


class ReportsQuery(BaseQuery):
    """Mirrors ReportListFilters."""

    status: Optional[ReportStatus] = None
    content_type: Optional[ReportableContentType] = None
    reason: Optional[ReportReason] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None


# ─── Statistics ───────────────────────────────────────────────────────────────

class ReasonCountOut(Schema):
    reason: ReportReason
    count: int


class ContentTypeCountOut(Schema):
    content_type: ReportableContentType
    count: int


class ModerationStatsOut(Schema):
    """Mirrors ModerationStats."""

    total_reports: int
    pending_reports: int
    resolved_this_week: int
    avg_resolution_time_hours: float
    reports_by_reason: List[ReasonCountOut] = []
    reports_by_content_type: List[ContentTypeCountOut] = []


# ─── Account deletion ─────────────────────────────────────────────────────────

class DeletionInfoOut(Schema):
    """Mirrors DeletionInfo."""

    status: DeletionStatus
    requested_at: Optional[str] = None
    grace_period_ends_at: Optional[str] = None
    completed_at: Optional[str] = None
    legal_hold_reason: Optional[str] = None
    legal_hold_by: Optional[ReviewerOut] = None
    legal_hold_at: Optional[str] = None


class UserWithDeletionOut(Schema):
    """Mirrors UserWithDeletionInfo."""

    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: str
    is_active: bool
    deletion: Optional[DeletionInfoOut] = None


class DeletionRequestIn(Schema):
    """Self-service erasure request. `reason` is optional and kept for context."""

    reason: Optional[str] = None


class CancelDeletionIn(Schema):
    reason: str


class LegalHoldIn(Schema):
    """Mirrors SetLegalHoldRequest."""

    reason: str


class DeletionStatusQuery(BaseQuery):
    deletion_status: Optional[DeletionStatus] = None
