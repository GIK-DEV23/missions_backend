from django.db import models
from django.utils import timezone


class PasswordResetToken(models.Model):
    """Single-use, short-lived token for the password reset flow.

    Only the SHA-256 hash of the token is stored — the raw token exists
    only in the reset email, never in the database.
    """
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return "Password reset token for {}".format(self.user.email)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
