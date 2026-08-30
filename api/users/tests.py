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
