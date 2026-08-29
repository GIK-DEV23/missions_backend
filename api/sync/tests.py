import uuid

from django.test import TestCase

from sync import services, selectors
from sync.constants import SyncEntity, SyncOp, SyncMutationStatus
from sync.models import SyncMutation
from souls.constants import SoulStatus
from souls.models import Soul
from users.constants import GenderType, AgeGroupCategory
from users.models import Role, User


def _mutation(**overrides):
    data = {
        "client_mutation_id": str(uuid.uuid4()),
        "entity": SyncEntity.SOUL,
        "client_id": uuid.uuid4(),
        "op": SyncOp.CREATE,
        "payload": {},
    }
    data.update(overrides)
    return data


def _soul_payload(**overrides):
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "+254700000021",
        "gender": GenderType.FEMALE,
        "age_group": AgeGroupCategory.ADULT,
        "status": SoulStatus.NEW_CONVERT,
        "date_added": "2026-01-01",
    }
    data.update(overrides)
    return data


class ApplyMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="missioner@example.com", password="pass12345")

    def test_create_soul_applied(self):
        client_id = uuid.uuid4()
        result = services.apply_mutation(self.user, _mutation(client_id=client_id, payload=_soul_payload()))
        self.assertEqual(result["status"], SyncMutationStatus.APPLIED)
        self.assertEqual(result["client_id"], str(client_id))
        self.assertIsNotNone(result["id"])

    def test_retry_same_client_mutation_id_is_duplicate(self):
        mutation = _mutation(payload=_soul_payload())
        first = services.apply_mutation(self.user, mutation)
        second = services.apply_mutation(self.user, mutation)
        self.assertEqual(first["status"], SyncMutationStatus.APPLIED)
        self.assertEqual(second["status"], SyncMutationStatus.DUPLICATE)
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(Soul.objects.count(), 1)

    def test_create_check_in_resolves_soul_client_id(self):
        soul_client_id = uuid.uuid4()
        soul_result = services.apply_mutation(
            self.user, _mutation(client_id=soul_client_id, payload=_soul_payload())
        )
        self.assertEqual(soul_result["status"], SyncMutationStatus.APPLIED)

        check_in_result = services.apply_mutation(self.user, _mutation(
            entity=SyncEntity.CHECK_IN,
            payload={"soul_client_id": soul_client_id, "content": "Checked in", "update_date": "2026-01-05"},
        ))
        self.assertEqual(check_in_result["status"], SyncMutationStatus.APPLIED)

    def test_update_unknown_client_id_is_conflict(self):
        result = services.apply_mutation(self.user, _mutation(
            op=SyncOp.UPDATE,
            payload={"first_name": "Someone"},
        ))
        self.assertEqual(result["status"], SyncMutationStatus.CONFLICT)

    def test_unknown_entity_is_rejected(self):
        result = services.apply_mutation(self.user, _mutation(entity="not_a_real_entity"))
        self.assertEqual(result["status"], SyncMutationStatus.REJECTED)

    def test_one_bad_mutation_does_not_roll_back_others(self):
        mutations = [
            _mutation(payload=_soul_payload(phone_number="+254700000031")),
            _mutation(entity="bogus"),
            _mutation(payload=_soul_payload(phone_number="+254700000032")),
        ]
        results = services.apply_mutations(self.user, mutations)
        self.assertEqual(results[0]["status"], SyncMutationStatus.APPLIED)
        self.assertEqual(results[1]["status"], SyncMutationStatus.REJECTED)
        self.assertEqual(results[2]["status"], SyncMutationStatus.APPLIED)
        self.assertEqual(Soul.objects.count(), 2)
        self.assertEqual(SyncMutation.objects.count(), 3)


class VisibleSoulsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.staff_user = User.objects.create_user(email="staff@example.com", password="pass12345")
        staff_role = Role.objects.create(name="staff", permissions=[])
        self.staff_user.roles.add(staff_role)

        self.personal_soul = Soul.objects.create(
            client_id=uuid.uuid4(), user=self.owner, is_personal=True, **_soul_payload(phone_number="+254700000041")
        )
        self.official_soul = Soul.objects.create(
            client_id=uuid.uuid4(), user=self.owner, is_personal=False, **_soul_payload(phone_number="+254700000042")
        )

    def test_owner_sees_both_souls(self):
        ids = set(selectors.visible_souls(self.owner).values_list("id", flat=True))
        self.assertEqual(ids, {self.personal_soul.id, self.official_soul.id})

    def test_staff_does_not_see_personal_soul(self):
        ids = set(selectors.visible_souls(self.staff_user).values_list("id", flat=True))
        self.assertIn(self.official_soul.id, ids)
        self.assertNotIn(self.personal_soul.id, ids)
