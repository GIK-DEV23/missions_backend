import datetime as dt
import importlib
import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from souls import services
from souls.constants import JourneyStage, ContactOutcome, ProgressUpdateType, ProgressUpdateOutcome
from souls.models import Soul
from users.constants import GenderType, AgeGroupCategory
from users.models import User


class ClientIdTests(TestCase):
    def _soul_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000001",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
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


class JourneyStageAndContactOutcomeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="pass1234",
            username="tester",
            first_name="Test",
            last_name="User",
        )

    def _soul_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000005",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
            "date_added": "2026-01-01",
        }
        data.update(overrides)
        return data

    def test_create_soul_stores_contact_outcome(self):
        soul = services.create_soul(self._soul_data(contact_outcome=ContactOutcome.BORN_AGAIN))
        self.assertEqual(soul.contact_outcome, ContactOutcome.BORN_AGAIN)

    def test_contact_outcome_is_immutable_once_set(self):
        soul = services.create_soul(self._soul_data(contact_outcome=ContactOutcome.BORN_AGAIN))
        with self.assertRaises(CustomValidationError):
            services.update_soul(user=self.user, soul_id=soul.id, data={"contact_outcome": ContactOutcome.NOT_YET})

    def test_contact_outcome_can_be_set_later_if_previously_unset(self):
        soul = services.create_soul(self._soul_data())
        updated = services.update_soul(user=self.user, soul_id=soul.id, data={"contact_outcome": ContactOutcome.ALREADY_BELIEVER})
        self.assertEqual(updated.contact_outcome, ContactOutcome.ALREADY_BELIEVER)

    def test_contact_outcome_update_to_same_value_allowed(self):
        soul = services.create_soul(self._soul_data(contact_outcome=ContactOutcome.NOT_YET))
        updated = services.update_soul(user=self.user, soul_id=soul.id, data={"contact_outcome": ContactOutcome.NOT_YET})
        self.assertEqual(updated.contact_outcome, ContactOutcome.NOT_YET)

    def test_status_data_migration_maps_legacy_values(self):
        migration = importlib.import_module(
            "souls.migrations.0004_soul_contact_outcome_alter_soul_status"
        )
        soul = services.create_soul(self._soul_data())
        Soul.objects.filter(id=soul.id).update(status="active")

        class _FakeApps:
            @staticmethod
            def get_model(app_label, name):
                return Soul

        migration.migrate_status_values(_FakeApps(), None)
        soul.refresh_from_db()
        self.assertEqual(soul.status, JourneyStage.GROWING)


class ProgressUpdateDetailsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="pass1234",
            username="author",
            first_name="Author",
            last_name="User",
        )
        self.soul = services.create_soul({
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000009",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
            "date_added": "2026-01-01",
        })

    def test_create_progress_update_sets_author_type_outcome(self):
        progress_update = services.create_progress_update({
            "soul_id": self.soul.id,
            "author_id": self.author.id,
            "content": "Called",
            "update_date": "2026-01-05",
            "type": ProgressUpdateType.CALL,
            "outcome": ProgressUpdateOutcome.REACHED,
        })
        self.assertEqual(progress_update.author_id, self.author.id)
        self.assertEqual(progress_update.type, ProgressUpdateType.CALL)
        self.assertEqual(progress_update.outcome, ProgressUpdateOutcome.REACHED)

    def test_create_progress_update_sets_last_contacted_at(self):
        self.assertIsNone(self.soul.last_contacted_at)
        services.create_progress_update({
            "soul_id": self.soul.id,
            "content": "Called",
            "update_date": "2026-01-05",
        })
        self.soul.refresh_from_db()
        self.assertIsNotNone(self.soul.last_contacted_at)

    def test_next_check_in_at_writes_through_to_soul_on_create(self):
        next_check_in = dt.datetime(2026, 2, 1, 9, 0, tzinfo=dt.timezone.utc)
        services.create_progress_update({
            "soul_id": self.soul.id,
            "content": "Called",
            "update_date": "2026-01-05",
            "next_check_in_at": next_check_in,
        })
        self.soul.refresh_from_db()
        self.assertEqual(self.soul.next_check_in_at, next_check_in)

    def test_next_check_in_at_writes_through_to_soul_on_update(self):
        progress_update = services.create_progress_update({
            "soul_id": self.soul.id,
            "content": "Called",
            "update_date": "2026-01-05",
        })
        next_check_in = dt.datetime(2026, 3, 1, 9, 0, tzinfo=dt.timezone.utc)
        services.update_progress_update(progress_update.id, {
            "next_check_in_at": next_check_in,
        })
        self.soul.refresh_from_db()
        self.assertEqual(self.soul.next_check_in_at, next_check_in)

    def test_delete_recomputes_last_contacted_at(self):
        first = services.create_progress_update({
            "soul_id": self.soul.id,
            "content": "First call",
            "update_date": "2026-01-01",
        })
        second = services.create_progress_update({
            "soul_id": self.soul.id,
            "content": "Second call",
            "update_date": "2026-01-05",
        })
        self.soul.refresh_from_db()
        self.assertEqual(self.soul.last_contacted_at, second.created_at)

        services.delete_progress_update(second.id)
        self.soul.refresh_from_db()
        self.assertEqual(self.soul.last_contacted_at, first.created_at)

        services.delete_progress_update(first.id)
        self.soul.refresh_from_db()
        self.assertIsNone(self.soul.last_contacted_at)


class ConsentDuplicateAndMergeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="carer@example.com",
            password="pass1234",
            username="carer",
            first_name="Carer",
            last_name="User",
        )

    def _soul_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000020",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
            "date_added": "2026-01-01",
        }
        data.update(overrides)
        return data

    def test_consent_recorded_at_stamped_when_consent_given_on_create(self):
        soul = services.create_soul(self._soul_data(consent_given=True))
        self.assertIsNotNone(soul.consent_recorded_at)

    def test_consent_recorded_at_not_stamped_without_consent(self):
        soul = services.create_soul(self._soul_data())
        self.assertIsNone(soul.consent_recorded_at)

    def test_explicit_consent_recorded_at_respected(self):
        explicit = dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc)
        soul = services.create_soul(self._soul_data(consent_given=True, consent_recorded_at=explicit))
        self.assertEqual(soul.consent_recorded_at, explicit)

    def test_do_not_contact_at_stamped_on_update(self):
        soul = services.create_soul(self._soul_data())
        self.assertIsNone(soul.do_not_contact_at)
        updated = services.update_soul(self.user, soul.id, {"do_not_contact": True})
        self.assertIsNotNone(updated.do_not_contact_at)

    def test_second_soul_with_same_phone_flagged_as_duplicate(self):
        original = services.create_soul(self._soul_data())
        duplicate = services.create_soul(self._soul_data(first_name="Janet"))
        self.assertEqual(duplicate.possible_duplicate_of_id, original.id)
        self.assertIsNone(original.possible_duplicate_of_id)

    def test_unique_phone_not_flagged(self):
        soul = services.create_soul(self._soul_data(phone_number="+254700000021"))
        self.assertIsNone(soul.possible_duplicate_of_id)

    def test_update_resolves_location_mission_user_fks(self):
        from missions.models import Location, MissionCategory, Mission
        from missions.constants import LocationCategoryType

        location = Location.objects.create(name="Nairobi", category=LocationCategoryType.TOWN, description="Capital")
        soul = services.create_soul(self._soul_data())
        updated = services.update_soul(self.user, soul.id, {"location": location.id, "user": self.user.id})
        self.assertEqual(updated.location_id, location.id)
        self.assertEqual(updated.user_id, self.user.id)

    def test_merge_reassigns_progress_updates_and_tombstones_duplicate(self):
        original = services.create_soul(self._soul_data())
        duplicate = services.create_soul(self._soul_data(first_name="Janet"))
        pu = services.create_progress_update({
            "soul_id": duplicate.id,
            "content": "Called",
            "update_date": "2026-01-02",
        })

        survivor = services.merge_souls(self.user, duplicate.id, original.id)

        self.assertEqual(survivor.id, original.id)
        pu.refresh_from_db()
        self.assertEqual(pu.soul_id, original.id)
        duplicate.refresh_from_db()
        self.assertIsNotNone(duplicate.deleted_at)

    def test_merge_clears_survivor_possible_duplicate_of(self):
        original = services.create_soul(self._soul_data())
        duplicate = services.create_soul(self._soul_data(first_name="Janet"))
        self.assertEqual(duplicate.possible_duplicate_of_id, original.id)

        survivor = services.merge_souls(self.user, original.id, duplicate.id)
        self.assertIsNone(survivor.possible_duplicate_of_id)

    def test_merged_soul_no_longer_resolvable(self):
        from souls.selectors import get_soul

        original = services.create_soul(self._soul_data())
        duplicate = services.create_soul(self._soul_data(first_name="Janet"))
        services.merge_souls(self.user, duplicate.id, original.id)

        with self.assertRaises(CustomValidationError):
            get_soul(duplicate.id)

    def test_cannot_merge_soul_into_itself(self):
        soul = services.create_soul(self._soul_data())
        with self.assertRaises(CustomValidationError):
            services.merge_souls(self.user, soul.id, soul.id)
