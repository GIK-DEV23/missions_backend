from django.core import mail
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from authentication import services
from authentication.models import PasswordResetToken
from base.utils.exceptions import CustomValidationError
from users.models import User


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset-me@example.com",
            password="OldPassword123!",
            username="resetme",
            first_name="Reset",
            last_name="Me",
        )

    def _issue_and_capture_token(self, email="reset-me@example.com"):
        mail.outbox = []
        services.request_password_reset(email)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        return body.split("token=")[1].strip()

    def test_request_reset_sends_email_for_known_user(self):
        services.request_password_reset("reset-me@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_request_reset_silent_for_unknown_email(self):
        services.request_password_reset("nobody@example.com")
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_password_with_valid_token_succeeds(self):
        raw_token = self._issue_and_capture_token()
        services.reset_password(raw_token, "BrandNewPassword456!")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPassword456!"))

    def test_token_is_single_use(self):
        raw_token = self._issue_and_capture_token()
        services.reset_password(raw_token, "BrandNewPassword456!")
        with self.assertRaises(CustomValidationError):
            services.reset_password(raw_token, "AnotherPassword789!")

    def test_expired_token_rejected(self):
        raw_token = self._issue_and_capture_token()
        token_hash = services._hash_token(raw_token)
        PasswordResetToken.objects.filter(token_hash=token_hash).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        with self.assertRaises(CustomValidationError):
            services.reset_password(raw_token, "BrandNewPassword456!")

    def test_unknown_token_rejected(self):
        with self.assertRaises(CustomValidationError):
            services.reset_password("not-a-real-token", "BrandNewPassword456!")

    def test_weak_password_rejected(self):
        raw_token = self._issue_and_capture_token()
        with self.assertRaises(CustomValidationError):
            services.reset_password(raw_token, "123")

    def test_successful_reset_invalidates_other_outstanding_tokens(self):
        first_token = self._issue_and_capture_token()
        second_token = self._issue_and_capture_token()
        services.reset_password(second_token, "BrandNewPassword456!")
        with self.assertRaises(CustomValidationError):
            services.reset_password(first_token, "YetAnotherPassword789!")
