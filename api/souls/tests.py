import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from souls import services
from souls.models import Soul
from souls.constants import SoulStatus
from users.constants import GenderType, AgeGroupCategory


class ClientIdTests(TestCase):
    def _soul_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000001",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": SoulStatus.NEW_CONVERT,
            "date_added": "2026-01-01",
        }
        data.update(overrides)
        return data

    def test_create_soul_echoes_client_id(self):
        client_id = uuid.uuid4()
        soul = services.create_soul(self._soul_data(client_id=client_id))
        self.assertEqual(soul.client_id, client_id)

    def test_duplicate_client_id_rejected(self):
        client_id = uuid.uuid4()
        services.create_soul(self._soul_data(client_id=client_id))
        with self.assertRaises(CustomValidationError):
            services.create_soul(self._soul_data(phone_number="+254700000002", client_id=client_id))

    def test_progress_update_resolves_soul_by_client_id(self):
        client_id = uuid.uuid4()
        soul = services.create_soul(self._soul_data(client_id=client_id))
        progress_update = services.create_progress_update({
            "soul_client_id": client_id,
            "content": "Checked in",
            "update_date": "2026-01-05",
        })
        self.assertEqual(progress_update.soul_id, soul.id)

    def test_progress_update_prefers_soul_id_when_both_given(self):
        soul = services.create_soul(self._soul_data(client_id=uuid.uuid4()))
        other_client_id = uuid.uuid4()
        progress_update = services.create_progress_update({
            "soul_id": soul.id,
            "soul_client_id": other_client_id,
            "content": "Checked in",
            "update_date": "2026-01-05",
        })
        self.assertEqual(progress_update.soul_id, soul.id)

    def test_progress_update_requires_soul_reference(self):
        with self.assertRaises(CustomValidationError):
            services.create_progress_update({
                "content": "Checked in",
                "update_date": "2026-01-05",
            })

    def test_progress_update_unknown_client_id_rejected(self):
        with self.assertRaises(CustomValidationError):
            services.create_progress_update({
                "soul_client_id": uuid.uuid4(),
                "content": "Checked in",
                "update_date": "2026-01-05",
            })

    def test_update_progress_update_resolves_soul_by_client_id(self):
        soul_a = services.create_soul(self._soul_data(client_id=uuid.uuid4()))
        soul_b_client_id = uuid.uuid4()
        soul_b = services.create_soul(self._soul_data(phone_number="+254700000003", client_id=soul_b_client_id))
        progress_update = services.create_progress_update({
            "soul_id": soul_a.id,
            "content": "Checked in",
            "update_date": "2026-01-05",
        })
        updated = services.update_progress_update(progress_update.id, {
            "soul_client_id": soul_b_client_id,
            "content": None,
            "update_date": None,
        })
        self.assertEqual(updated.soul_id, soul_b.id)
