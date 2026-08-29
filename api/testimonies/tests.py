import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from souls import services as soul_services
from souls.constants import JourneyStage
from testimonies import services
from users.constants import GenderType, AgeGroupCategory


class ClientIdTests(TestCase):
    def _make_soul(self, client_id=None):
        return soul_services.create_soul({
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000001",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
            "date_added": "2026-01-01",
            "client_id": client_id or uuid.uuid4(),
        })

    def test_create_testimony_resolves_soul_by_client_id(self):
        soul_client_id = uuid.uuid4()
        soul = self._make_soul(soul_client_id)
        testimony = services.create_testimony({
            "title": "Healed",
            "content": "Testimony content",
            "soul_client_id": soul_client_id,
        })
        self.assertEqual(testimony.soul_id, soul.id)

    def test_create_testimony_unknown_soul_client_id_rejected(self):
        with self.assertRaises(CustomValidationError):
            services.create_testimony({
                "title": "Healed",
                "content": "Testimony content",
                "soul_client_id": uuid.uuid4(),
            })

    def test_create_miracle_resolves_soul_by_client_id(self):
        soul_client_id = uuid.uuid4()
        soul = self._make_soul(soul_client_id)
        miracle = services.create_miracle({
            "title": "Miracle",
            "content": "Miracle content",
            "soul_client_id": soul_client_id,
        })
        self.assertEqual(miracle.soul_id, soul.id)
