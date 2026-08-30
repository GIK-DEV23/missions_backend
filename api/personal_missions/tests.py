import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from personal_missions import services, selectors
from personal_missions.constants import PersonalMissionType, PersonalMissionRhythm
from personal_missions.models import PersonalMission
from users.models import User


class PersonalMissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="pass1234",
            username="owner",
            first_name="Owner",
            last_name="User",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="pass1234",
            username="other",
            first_name="Other",
            last_name="User",
        )

    def _data(self, **overrides):
        data = {
            "name": "Weekly street outreach",
            "type": PersonalMissionType.ONGOING,
            "start_date": "2026-01-01",
            "rhythm": PersonalMissionRhythm.WEEKLY,
            "rhythm_day": 6,
            "reminder_enabled": True,
        }
        data.update(overrides)
        return data

    def test_create_stores_client_id_and_owner(self):
        client_id = uuid.uuid4()
        pm = services.create_personal_mission(self.owner, self._data(client_id=client_id))
        self.assertEqual(pm.client_id, client_id)
        self.assertEqual(pm.owner_id, self.owner.id)

    def test_what_happened_rejected_for_ongoing(self):
        with self.assertRaises(CustomValidationError):
            services.create_personal_mission(self.owner, self._data(what_happened="Led 3 people to Christ"))

    def test_what_happened_allowed_for_one_time(self):
        pm = services.create_personal_mission(self.owner, self._data(
            type=PersonalMissionType.ONE_TIME,
            what_happened="Led 3 people to Christ",
        ))
        self.assertEqual(pm.what_happened, "Led 3 people to Christ")

    def test_rhythm_day_out_of_range_rejected(self):
        with self.assertRaises(CustomValidationError):
            services.create_personal_mission(self.owner, self._data(rhythm_day=7))

    def test_list_is_owner_scoped(self):
        services.create_personal_mission(self.owner, self._data())
        services.create_personal_mission(self.other_user, self._data(name="Other's mission"))
        owner_list = list(selectors.list_personal_missions(self.owner))
        self.assertEqual(len(owner_list), 1)
        self.assertEqual(owner_list[0].owner_id, self.owner.id)

    def test_cannot_access_another_users_personal_mission(self):
        pm = services.create_personal_mission(self.other_user, self._data())
        with self.assertRaises(CustomValidationError):
            selectors.get_personal_mission(self.owner, pm.id)

    def test_update_switching_to_ongoing_with_what_happened_rejected(self):
        pm = services.create_personal_mission(self.owner, self._data(
            type=PersonalMissionType.ONE_TIME,
            what_happened="Led 3 people to Christ",
        ))
        with self.assertRaises(CustomValidationError):
            services.update_personal_mission(self.owner, pm.id, {"type": PersonalMissionType.ONGOING})

    def test_update_can_clear_what_happened_while_switching_to_ongoing(self):
        pm = services.create_personal_mission(self.owner, self._data(
            type=PersonalMissionType.ONE_TIME,
            what_happened="Led 3 people to Christ",
        ))
        updated = services.update_personal_mission(self.owner, pm.id, {
            "type": PersonalMissionType.ONGOING,
            "what_happened": None,
        })
        self.assertEqual(updated.type, PersonalMissionType.ONGOING)
        self.assertIsNone(updated.what_happened)

    def test_update_can_clear_a_nullable_field(self):
        pm = services.create_personal_mission(self.owner, self._data(location="Nairobi CBD"))
        updated = services.update_personal_mission(self.owner, pm.id, {"location": None})
        self.assertIsNone(updated.location)

    def test_archive_sets_archived_at(self):
        pm = services.create_personal_mission(self.owner, self._data())
        self.assertIsNone(pm.archived_at)
        archived = services.archive_personal_mission(self.owner, pm.id)
        self.assertIsNotNone(archived.archived_at)
        self.assertTrue(archived.is_archived)
