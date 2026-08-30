import uuid

from django.test import TestCase

from sync import services, selectors
from sync.constants import SyncEntity, SyncOp, SyncMutationStatus
from sync.models import SyncMutation
from souls.constants import JourneyStage
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
        "status": JourneyStage.NEW_BELIEVER,
        "date_added": "2026-01-01",
    }
    data.update(overrides)
    return data


class ApplyMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="missioner@example.com", password="pass12345", is_superuser=True
        )

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

    def test_delete_reports_the_deleted_id(self):
        client_id = uuid.uuid4()
        created = services.apply_mutation(self.user, _mutation(client_id=client_id, payload=_soul_payload()))
        deleted = services.apply_mutation(self.user, _mutation(client_id=client_id, op=SyncOp.DELETE))
        self.assertEqual(deleted["status"], SyncMutationStatus.APPLIED)
        self.assertEqual(deleted["id"], created["id"])
        self.assertIsNotNone(deleted["id"])

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

    def test_oversized_entity_string_is_rejected_not_crashed(self):
        result = services.apply_mutation(self.user, _mutation(entity="x" * 500))
        self.assertEqual(result["status"], SyncMutationStatus.REJECTED)


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


class OwnershipRestrictionTests(TestCase):
    """A missioner-only user can only touch their own souls via sync; staff can touch anyone's."""

    def setUp(self):
        self.owner = User.objects.create_user(email="owner2@example.com", password="pass12345")
        self.missioner = User.objects.create_user(email="missioner2@example.com", password="pass12345")
        self.staff_user = User.objects.create_user(email="staff2@example.com", password="pass12345")
        self.missioner.roles.add(Role.objects.create(name="missioner_template", permissions=["update_soul"]))
        self.staff_user.roles.add(Role.objects.create(name="staff", permissions=["update_soul"]))
        self.soul = Soul.objects.create(
            client_id=uuid.uuid4(), user=self.owner, is_personal=False,
            **_soul_payload(phone_number="+254700000051")
        )

    def test_missioner_cannot_update_soul_they_do_not_own(self):
        result = services.apply_mutation(self.missioner, _mutation(
            client_id=self.soul.client_id, op=SyncOp.UPDATE, payload={"description": "hi"}
        ))
        self.assertEqual(result["status"], SyncMutationStatus.REJECTED)

    def test_staff_can_update_soul_they_do_not_own(self):
        result = services.apply_mutation(self.staff_user, _mutation(
            client_id=self.soul.client_id, op=SyncOp.UPDATE, payload={"description": "hi"}
        ))
        self.assertEqual(result["status"], SyncMutationStatus.APPLIED)


class PermissionGateTests(TestCase):
    """Sync enforces the same per-operation permission the direct REST endpoint would."""

    def setUp(self):
        self.no_perms_user = User.objects.create_user(email="noperm@example.com", password="pass12345")
        self.authorized_user = User.objects.create_user(email="authorized@example.com", password="pass12345")
        self.authorized_user.roles.add(Role.objects.create(name="missioner_template2", permissions=["create_soul"]))

    def test_user_without_create_soul_permission_is_rejected(self):
        result = services.apply_mutation(self.no_perms_user, _mutation(payload=_soul_payload()))
        self.assertEqual(result["status"], SyncMutationStatus.REJECTED)
        self.assertIn("Permission denied", result["error"])

    def test_user_with_create_soul_permission_is_applied(self):
        result = services.apply_mutation(self.authorized_user, _mutation(payload=_soul_payload()))
        self.assertEqual(result["status"], SyncMutationStatus.APPLIED)


class ChangesSinceDeletedSoulsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner3@example.com", password="pass12345")
        self.staff_user = User.objects.create_user(email="staff3@example.com", password="pass12345")
        self.staff_user.roles.add(Role.objects.create(name="staff3", permissions=[]))

    def test_merged_soul_reported_as_deleted_since_the_merge(self):
        from django.utils import timezone
        from souls import services as soul_services

        original = soul_services.create_soul(_soul_payload(phone_number="+254700000061", user=self.owner.id))
        duplicate = soul_services.create_soul(_soul_payload(phone_number="+254700000062", first_name="Janet", user=self.owner.id))

        before_merge = timezone.now()
        soul_services.merge_souls(self.owner, duplicate.id, original.id)

        changes = selectors.changes_since(self.owner, before_merge)
        self.assertIn(duplicate.id, changes["deleted"]["souls"])
        self.assertNotIn(duplicate.id, [s["id"] for s in changes["souls"]])

    def test_no_since_means_no_deleted_list(self):
        changes = selectors.changes_since(self.owner, None)
        self.assertEqual(changes["deleted"]["souls"], [])


class VisibleTestimoniesTests(TestCase):
    def setUp(self):
        from testimonies.models import Testimony

        self.owner = User.objects.create_user(email="owner4@example.com", password="pass12345")
        self.staff_user = User.objects.create_user(email="staff4@example.com", password="pass12345")
        self.staff_user.roles.add(Role.objects.create(name="staff4", permissions=[]))

        self.personal = Testimony.objects.create(title="t1", content="c1", user=self.owner, is_personal=True)
        self.official = Testimony.objects.create(title="t2", content="c2", user=self.owner, is_personal=False)

    def test_staff_does_not_see_personal_testimony(self):
        ids = set(selectors.visible_testimonies(self.staff_user).values_list("id", flat=True))
        self.assertIn(self.official.id, ids)
        self.assertNotIn(self.personal.id, ids)

    def test_owner_sees_both_testimonies(self):
        ids = set(selectors.visible_testimonies(self.owner).values_list("id", flat=True))
        self.assertEqual(ids, {self.personal.id, self.official.id})
