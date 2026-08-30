from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from notifications import services, selectors
from users.models import User


class NotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="notif-owner@example.com", password="pass1234",
            username="notifowner", first_name="Notif", last_name="Owner",
        )
        self.other_user = User.objects.create_user(
            email="notif-other@example.com", password="pass1234",
            username="notifother", first_name="Notif", last_name="Other",
        )

    def test_create_notification_stores_fields(self):
        notification = services.create_notification(
            self.owner, title="Check-in due", body="Time to follow up.", type="check_in_reminder"
        )
        self.assertEqual(notification.user_id, self.owner.id)
        self.assertEqual(notification.title, "Check-in due")
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_list_is_owner_scoped(self):
        services.create_notification(self.owner, title="For owner")
        services.create_notification(self.other_user, title="For other")
        owned = list(selectors.list_notifications(self.owner))
        self.assertEqual(len(owned), 1)
        self.assertEqual(owned[0].title, "For owner")

    def test_mark_notification_read_sets_timestamp(self):
        notification = services.create_notification(self.owner, title="Test")
        updated = services.mark_notification_read(self.owner, notification.id)
        self.assertTrue(updated.is_read)
        self.assertIsNotNone(updated.read_at)

    def test_marking_already_read_notification_is_idempotent(self):
        notification = services.create_notification(self.owner, title="Test")
        first = services.mark_notification_read(self.owner, notification.id)
        second = services.mark_notification_read(self.owner, notification.id)
        self.assertEqual(first.read_at, second.read_at)

    def test_cannot_mark_another_users_notification_read(self):
        notification = services.create_notification(self.other_user, title="Not yours")
        with self.assertRaises(CustomValidationError):
            services.mark_notification_read(self.owner, notification.id)
