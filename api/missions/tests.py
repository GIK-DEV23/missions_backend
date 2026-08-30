import datetime
import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from missions import services, selectors
from missions.constants import LocationCategoryType, PaymentTiming, PaymentStatus, RegistrationStatus
from missions.models import Location, MissionCategory, Mission
from users.constants import GenderType
from users.models import User


class ClientIdTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="staffer@example.com",
            password="pass1234",
            username="staffer",
            first_name="Staff",
            last_name="User",
        )
        self.location = Location.objects.create(
            name="Nairobi",
            category=LocationCategoryType.TOWN,
            description="Capital",
        )
        self.category = MissionCategory.objects.create(name="Outreach")
        self.mission = Mission.objects.create(
            title="Nairobi Outreach",
            description="Desc",
            category=self.category,
            location=self.location,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 1),
        )

    def test_create_mission_stores_client_id(self):
        client_id = uuid.uuid4()
        mission = services.create_mission(
            title="Kisumu Outreach",
            description="Desc",
            category_id=self.category.id,
            location_id=self.location.id,
            start_date=datetime.date(2026, 4, 1),
            end_date=datetime.date(2026, 4, 1),
            user=None,
            client_id=client_id,
        )
        self.assertEqual(mission.client_id, client_id)

    def test_create_mission_participant_stores_client_id(self):
        client_id = uuid.uuid4()
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="John Doe",
            phone_number="+254700000010",
            diet_advisory="",
            client_id=client_id,
        )
        self.assertEqual(participant.client_id, client_id)

    def test_duplicate_participant_gives_friendly_message(self):
        kwargs = dict(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="John Doe",
            phone_number="+254700000010",
            diet_advisory="",
        )
        services.create_mission_participant(**kwargs)
        with self.assertRaises(CustomValidationError) as ctx:
            services.create_mission_participant(**kwargs)
        self.assertIn("already exists", str(ctx.exception.errors))

    def test_create_mission_participant_stores_payment_timing(self):
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000011",
            diet_advisory="",
            payment_timing=PaymentTiming.PAY_LATER,
        )
        self.assertEqual(participant.payment_timing, PaymentTiming.PAY_LATER)

    def test_update_mission_participant_changes_payment_timing(self):
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000012",
            diet_advisory="",
        )
        self.assertIsNone(participant.payment_timing)
        updated = services.update_mission_participant(
            user=self.user, update_dict={"payment_timing": PaymentTiming.ON_ARRIVAL}, participant_id=participant.id
        )
        self.assertEqual(updated.payment_timing, PaymentTiming.ON_ARRIVAL)

    def test_bulk_create_gallery_images(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile("test.jpg", b"fake image bytes", content_type="image/jpeg")
        images = services.bulk_create_gallery_images(
            mission_id=self.mission.id,
            uploaded_by_id=self.user.id,
            images_data=[{"image": image, "title": "Front view", "description": "Morning"}],
        )
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].title, "Front view")
        self.assertEqual(images[0].mission_id, self.mission.id)

    def test_participant_defaults_unpaid_pending(self):
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000013",
            diet_advisory="",
        )
        self.assertEqual(participant.payment_status, PaymentStatus.UNPAID)
        self.assertEqual(participant.status, RegistrationStatus.PENDING)
        self.assertFalse(participant.consent_code_of_conduct)
        self.assertFalse(participant.consent_photo)

    def test_participant_stores_consents_on_create(self):
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000014",
            diet_advisory="",
            consent_code_of_conduct=True,
            consent_photo=True,
        )
        self.assertTrue(participant.consent_code_of_conduct)
        self.assertTrue(participant.consent_photo)

    def test_registration_never_blocked_by_payment_status(self):
        # Creating a registration never requires/derives from payment_status —
        # it's not even an accepted create-time field, always starts unpaid.
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000015",
            diet_advisory="",
        )
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.payment_status, PaymentStatus.UNPAID)

    def test_update_changes_payment_status_and_registration_status(self):
        participant = services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Jane Roe",
            phone_number="+254700000016",
            diet_advisory="",
        )
        updated = services.update_mission_participant(
            user=self.user,
            update_dict={"payment_status": PaymentStatus.PAID, "status": RegistrationStatus.CONFIRMED},
            participant_id=participant.id,
        )
        self.assertEqual(updated.payment_status, PaymentStatus.PAID)
        self.assertEqual(updated.status, RegistrationStatus.CONFIRMED)

    def test_my_registrations_scoped_to_user(self):
        other_user = User.objects.create_user(
            email="other-reg@example.com", password="pass1234",
            username="otherreg", first_name="Other", last_name="Reg",
        )
        services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Mine",
            phone_number="+254700000017",
            diet_advisory="",
            user_id=self.user.id,
        )
        services.create_mission_participant(
            mission_id=self.mission.id,
            travelling_from="Mombasa",
            days_of_attendance=[{"day": 1, "day_date": datetime.date(2026, 3, 1)}],
            gender=GenderType.MALE,
            full_name="Not mine",
            phone_number="+254700000018",
            diet_advisory="",
            user_id=other_user.id,
        )
        mine = list(selectors.my_registrations(self.user))
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0].full_name, "Mine")

    def test_create_mission_stores_souls_reached(self):
        mission = services.create_mission(
            title="Souls Reached Test",
            description="Desc",
            category_id=self.category.id,
            location_id=self.location.id,
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 1),
            user=None,
            souls_reached=500,
        )
        self.assertEqual(mission.souls_reached, 500)

    def test_update_mission_changes_souls_reached(self):
        updated = services.update_mission(
            user=self.user, update_dict={"souls_reached": 250}, mission_id=self.mission.id
        )
        self.assertEqual(updated.souls_reached, 250)

    def test_mission_souls_reached_defaults_to_none(self):
        self.assertIsNone(self.mission.souls_reached)

    def test_created_by_is_set_and_exposed_in_schema(self):
        from missions import schemas

        mission = services.create_mission(
            title="Authorship Test",
            description="Desc",
            category_id=self.category.id,
            location_id=self.location.id,
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 1),
            user=self.user,
        )
        self.assertEqual(mission.created_by_id, self.user.id)

        # This is the actual regression: to_dict() already had these keys,
        # but the pydantic output schema silently dropped them.
        out = schemas.MissionOutSchema(**mission.to_dict())
        self.assertEqual(out.created_by_id, self.user.id)
        self.assertIn(self.user.email, out.created_by_name)
