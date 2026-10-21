"""Moderation models: reactive content reports and the account erasure record.

Both shapes come from the clients (BR-1). ContentReport matches the dashboard's
`ContentReport` interface and the mobile `ContentReport` model; UserDeletion
matches the `DeletionInfo` object the dashboard nests under a user.
"""

from typing import Any, Dict, Optional

from django.db import models
from django.http import HttpRequest

from base.models import BaseModel, client_id_field
from moderation.constants import (
    DeletionStatus,
    ReportableContentType,
    ReportReason,
    ReportStatus,
)


class ContentReport(BaseModel):
    """One report raised by a user against a piece of content.

    The target is a (content_type, content_id) pair rather than a real
    ForeignKey because four unrelated tables are reportable and the clients
    already address them that way. The trade-off is that a deleted target
    leaves a dangling id, which `resolve_content_preview` reports as missing
    rather than raising.
    """

    #: UUID the mobile client assigns offline, so a queued report that syncs
    #: twice is recorded once. See moderation.services.create_report.
    client_id = client_id_field()

    content_type = models.CharField(
        max_length=20,
        choices=ReportableContentType.choices,
        help_text="Which table content_id refers to",
    )
    content_id = models.PositiveIntegerField(
        help_text="Primary key of the reported row, within content_type",
    )
    reporter = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports",
        help_text="Who reported it. Null for an anonymous report, and nulled "
                  "when the reporter's account is erased.",
    )
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    details = models.TextField(
        blank=True,
        default="",
        help_text="Free text the reporter added",
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_content_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(
        blank=True,
        default="",
        help_text="What the reviewer decided and why",
    )

    class Meta:
        db_table = "content_reports"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["reason"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            # One reporter may not pile up duplicate open reports on the same
            # item; a retried offline sync carries the same client_id.
            models.UniqueConstraint(
                fields=["reporter", "content_type", "content_id"],
                condition=models.Q(status__in=["pending", "under_review"]),
                name="uniq_open_report_per_reporter_and_content",
            ),
        ]

    def __str__(self):
        return "Report #{} on {} #{} ({})".format(
            self.pk, self.content_type, self.content_id, self.status
        )

    def to_dict(
        self,
        request: Optional[HttpRequest] = None,
        include_preview: bool = False,
    ) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "reporter": (
                {
                    "id": self.reporter.pk,
                    "name": self.reporter.get_full_name(),
                    "email": self.reporter.email,
                }
                if self.reporter
                else None
            ),
            "reviewed_by": (
                {"id": self.reviewed_by.pk, "name": self.reviewed_by.get_full_name()}
                if self.reviewed_by
                else None
            ),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        })
        if include_preview:
            # Imported here: selectors imports this module.
            from moderation.selectors import resolve_content_preview

            data["content_preview"] = resolve_content_preview(
                self.content_type, self.content_id
            )
        return data


class UserDeletion(BaseModel):
    """Erasure record for one account.

    A user with no row here has never requested deletion, which the API reports
    as `deletion: null`. The row is created on request and kept afterwards as
    the evidence that erasure happened and when.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="deletion",
    )
    status = models.CharField(
        max_length=25,
        choices=DeletionStatus.choices,
        default=DeletionStatus.DELETION_REQUESTED,
    )
    requested_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Erasure may not run before this instant; the user can cancel until then",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")

    legal_hold_reason = models.TextField(blank=True, default="")
    legal_hold_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legal_holds_placed",
    )
    legal_hold_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_deletions"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["grace_period_ends_at"]),
        ]

    def __str__(self):
        return "Deletion[{}] for user {}".format(self.status, self.user_id)

    @property
    def is_on_legal_hold(self) -> bool:
        return self.status == DeletionStatus.LEGAL_HOLD

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "grace_period_ends_at": (
                self.grace_period_ends_at.isoformat() if self.grace_period_ends_at else None
            ),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "legal_hold_at": self.legal_hold_at.isoformat() if self.legal_hold_at else None,
            "legal_hold_reason": self.legal_hold_reason or None,
            "legal_hold_by": (
                {"id": self.legal_hold_by.pk, "name": self.legal_hold_by.get_full_name()}
                if self.legal_hold_by
                else None
            ),
        })
        return data
