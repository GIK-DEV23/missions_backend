from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from users import services
from users.constants import GenderType
from users.models import User


class SelfServeProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="pass1234",
            username="profileuser",
            first_name="Profile",
            last_name="User",
        )

    def test_update_sets_new_fields(self):
        updated = services.update_own_profile(self.user, {
            "phone_number": "+254700000030",
            "church": "GIK Church",
            "bio": "Loves outreach.",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "+254700000031",
        })
        self.assertEqual(str(updated.phone_number), "+254700000030")
        self.assertEqual(updated.church, "GIK Church")
        self.assertEqual(updated.bio, "Loves outreach.")

    def test_update_stores_saved_partner(self):
        updated = services.update_own_profile(self.user, {
            "saved_partner": {
                "name": "John Doe",
                "gender": GenderType.MALE,
                "traveling_from": "Nairobi",
                "dietary": "Vegetarian",
            }
        })
        self.assertEqual(updated.saved_partner["name"], "John Doe")

    def test_update_can_clear_a_field(self):
        services.update_own_profile(self.user, {"bio": "Initial bio"})
        updated = services.update_own_profile(self.user, {"bio": None})
        self.assertIsNone(updated.bio)

    def test_to_dict_omits_phone_when_unset(self):
        data = self.user.to_dict()
        self.assertIsNone(data["phone_number"])
        self.assertIsNone(data["emergency_contact_phone"])

    def test_full_clean_rejects_invalid_data(self):
        with self.assertRaises(CustomValidationError):
            services.update_own_profile(self.user, {"phone_number": "not-a-phone-number"})


class DataRightsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dpa@example.com",
            password="pass1234",
            username="dpauser",
            first_name="Dpa",
            last_name="User",
        )

    def test_export_includes_profile_and_empty_collections(self):
        data = services.export_user_data(self.user)
        self.assertEqual(data["profile"]["email"], "dpa@example.com")
        for key in ("souls", "progress_updates", "testimonies", "miracles", "highlights", "personal_missions", "registrations", "notifications"):
            self.assertEqual(data[key], [])

    def test_export_includes_owned_soul(self):
        from souls import services as soul_services
        from souls.constants import JourneyStage
        from users.constants import AgeGroupCategory

        soul_services.create_soul({
            "first_name": "Jane", "last_name": "Doe", "phone_number": "+254700000090",
            "gender": GenderType.FEMALE, "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER, "date_added": "2026-01-01",
            "user": self.user.id,
        })
        data = services.export_user_data(self.user)
        self.assertEqual(len(data["souls"]), 1)

    def test_request_account_deletion_deactivates_and_stamps(self):
        self.assertIsNone(self.user.deletion_requested_at)
        updated = services.request_account_deletion(self.user)
        self.assertFalse(updated.is_active)
        self.assertIsNotNone(updated.deletion_requested_at)
