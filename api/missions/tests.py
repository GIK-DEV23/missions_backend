import datetime
import uuid

from django.test import TestCase

from base.utils.exceptions import CustomValidationError
from missions import services
from missions.constants import LocationCategoryType
from missions.models import Location, MissionCategory, Mission
from users.constants import GenderType


class ClientIdTests(TestCase):
    def setUp(self):
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
