from typing import Dict, Any

from django.db import models
from django.http import HttpRequest

from audit_logs.constants import ActionType, ContentType
from base.models import BaseModel


class AuditLog(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.PROTECT)
    action_type = models.CharField(choices=ActionType.choices, max_length=50)
    action_category = models.CharField(max_length=100)
    action_description = models.CharField(max_length=300)
    is_successful = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    flag_suspicious = models.BooleanField(default=False)
    # Moderation-specific fields (nullable for non-moderation logs)
    content_type = models.CharField(
        choices=ContentType.choices,
        max_length=50,
        null=True,
        blank=True,
        help_text="Type of content being moderated (testimony, miracle)"
    )
    content_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the content being moderated"
    )
    previous_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Status before this moderation action"
    )
    new_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Status after this moderation action"
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason for rejection (if action_type is REJECT)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['action_category']),
            models.Index(fields=['is_successful']),
            models.Index(fields=['flag_suspicious']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['action_type', 'action_category']),
        ]
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"AuditLog {self.pk} - {self.action_category} by User {self.user.pk}"

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user.id if self.user else None,
            "user_name": self.user.get_full_name() if self.user else None,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "rejection_reason": self.rejection_reason,
        })
        return data