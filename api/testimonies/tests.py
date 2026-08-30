import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from souls import services as soul_services
from souls.constants import JourneyStage
from testimonies import services, selectors
from testimonies.constants import ReviewStatus, SubmissionVisibility
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


class ReviewWorkflowTests(TestCase):
    def test_testimony_defaults_to_pending_public(self):
        testimony = services.create_testimony({"title": "T", "content": "C"})
        self.assertEqual(testimony.review_status, ReviewStatus.PENDING)
        self.assertEqual(testimony.visibility, SubmissionVisibility.PUBLIC)
        self.assertIsNone(testimony.rejection_reason)

    def test_approve_testimony_clears_prior_rejection(self):
        testimony = services.create_testimony({"title": "T", "content": "C"})
        services.reject_testimony(testimony.id, "Not appropriate")
        approved = services.approve_testimony(testimony.id)
        self.assertEqual(approved.review_status, ReviewStatus.APPROVED)
        self.assertIsNone(approved.rejection_reason)

    def test_reject_testimony_stores_reason(self):
        testimony = services.create_testimony({"title": "T", "content": "C"})
        rejected = services.reject_testimony(testimony.id, "Contains identifying details")
        self.assertEqual(rejected.review_status, ReviewStatus.REJECTED)
        self.assertEqual(rejected.rejection_reason, "Contains identifying details")

    def test_create_testimony_accepts_visibility_and_consent(self):
        testimony = services.create_testimony({
            "title": "T", "content": "C",
            "visibility": SubmissionVisibility.ANONYMOUS,
            "third_party_consent": True,
        })
        self.assertEqual(testimony.visibility, SubmissionVisibility.ANONYMOUS)
        self.assertTrue(testimony.third_party_consent)

    def test_miracle_approve_reject_mirror_testimony(self):
        miracle = services.create_miracle({"title": "M", "content": "C"})
        self.assertEqual(miracle.review_status, ReviewStatus.PENDING)
        rejected = services.reject_miracle(miracle.id, "Needs more detail")
        self.assertEqual(rejected.review_status, ReviewStatus.REJECTED)
        approved = services.approve_miracle(miracle.id)
        self.assertEqual(approved.review_status, ReviewStatus.APPROVED)
        self.assertIsNone(approved.rejection_reason)

    def test_testimony_can_link_personal_mission(self):
        from personal_missions import services as pm_services
        from personal_missions.constants import PersonalMissionType
        from users.models import User

        owner = User.objects.create_user(
            email="pm-owner@example.com", password="pass1234",
            username="pmowner", first_name="PM", last_name="Owner",
        )
        pm = pm_services.create_personal_mission(owner, {
            "name": "Street outreach", "type": PersonalMissionType.ONE_TIME,
            "start_date": "2026-01-01",
        })
        testimony = services.create_testimony({
            "title": "T", "content": "C",
            "personal_mission_id": pm.id, "is_personal": True,
        })
        self.assertEqual(testimony.personal_mission_id, pm.id)
        self.assertTrue(testimony.is_personal)


class HighlightTests(TestCase):
    def test_highlight_defaults_to_pending_public(self):
        highlight = services.create_highlight({"title": "H", "content": "C"})
        self.assertEqual(highlight.review_status, ReviewStatus.PENDING)
        self.assertEqual(highlight.visibility, SubmissionVisibility.PUBLIC)

    def test_highlight_resolves_soul_by_client_id(self):
        soul_client_id = uuid.uuid4()
        soul = soul_services.create_soul({
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+254700000002",
            "gender": GenderType.FEMALE,
            "age_group": AgeGroupCategory.ADULT,
            "status": JourneyStage.NEW_BELIEVER,
            "date_added": "2026-01-01",
            "client_id": soul_client_id,
        })
        highlight = services.create_highlight({
            "title": "H", "content": "C", "soul_client_id": soul_client_id,
        })
        self.assertEqual(highlight.soul_id, soul.id)

    def test_highlight_approve_reject(self):
        highlight = services.create_highlight({"title": "H", "content": "C"})
        rejected = services.reject_highlight(highlight.id, "Needs more detail")
        self.assertEqual(rejected.review_status, ReviewStatus.REJECTED)
        approved = services.approve_highlight(highlight.id)
        self.assertEqual(approved.review_status, ReviewStatus.APPROVED)
        self.assertIsNone(approved.rejection_reason)

    def test_highlight_update_and_delete(self):
        from testimonies.selectors import highlight_details

        highlight = services.create_highlight({"title": "H", "content": "C"})
        updated = services.update_highlight(highlight.id, {"title": "Updated title"})
        self.assertEqual(updated.title, "Updated title")
        highlight_id = highlight.id
        services.delete_highlight(highlight_id)
        with self.assertRaises(CustomValidationError):
            highlight_details(highlight_id)


class MultiPhotoTests(TestCase):
    def _fake_image(self, name="photo.jpg"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, b"fake image bytes", content_type="image/jpeg")

    def test_bulk_create_testimony_photos(self):
        testimony = services.create_testimony({"title": "T", "content": "C"})
        photos = services.bulk_create_testimony_photos(testimony.id, [
            {"image": self._fake_image("a.jpg"), "title": "First", "description": "d1"},
            {"image": self._fake_image("b.jpg"), "title": "Second", "description": "d2"},
        ])
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0].testimony_id, testimony.id)
        self.assertEqual(selectors.testimony_photos_list(testimony.id).count(), 2)

    def test_bulk_create_miracle_photos(self):
        miracle = services.create_miracle({"title": "M", "content": "C"})
        photos = services.bulk_create_miracle_photos(miracle.id, [
            {"image": self._fake_image("a.jpg"), "title": "First", "description": ""},
        ])
        self.assertEqual(len(photos), 1)
        self.assertEqual(selectors.miracle_photos_list(miracle.id).count(), 1)

    def test_bulk_create_highlight_photos(self):
        highlight = services.create_highlight({"title": "H", "content": "C"})
        photos = services.bulk_create_highlight_photos(highlight.id, [
            {"image": self._fake_image("a.jpg"), "title": "First", "description": ""},
        ])
        self.assertEqual(len(photos), 1)
        self.assertEqual(selectors.highlight_photos_list(highlight.id).count(), 1)

    def test_photos_for_unknown_testimony_rejected(self):
        with self.assertRaises(CustomValidationError):
            services.bulk_create_testimony_photos(999999, [
                {"image": self._fake_image(), "title": "", "description": ""},
            ])
