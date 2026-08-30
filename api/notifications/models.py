from typing import Any, Dict, Optional

from django.db import models
from django.http import HttpRequest

from base.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    type = models.CharField(max_length=50, null=True, blank=True, help_text="Free-form event tag, e.g. 'check_in_reminder'")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return self.title

    def to_dict(self, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user.id if self.user else None,
        })
        return data
