from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Event

User = get_user_model()

class EventAutoDeleteTests(APITestCase):

    def setUp(self):
        # Create an organizer user
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="TestPassword123!",
            role="organizer"
        )
        self.events_url = reverse("event-list-create")

    def test_auto_delete_expired_events(self):
        """
        Verify that events expired for more than 24 hours are automatically deleted,
        while events expired for less than 24 hours or upcoming are kept.
        """
        now = timezone.now()

        # 1. Event expired 25 hours ago (should be deleted)
        event_old = Event.objects.create(
            title="Old Event",
            description="Expired > 24h ago",
            category="music",
            date=now - timedelta(hours=25),
            venue_name="Venue A",
            price=10.00,
            organizer=self.organizer,
            total_tickets=100,
            is_published=True
        )

        # 2. Event expired 12 hours ago (should be kept)
        event_recent = Event.objects.create(
            title="Recent Event",
            description="Expired < 24h ago",
            category="tech",
            date=now - timedelta(hours=12),
            venue_name="Venue B",
            price=20.00,
            organizer=self.organizer,
            total_tickets=100,
            is_published=True
        )

        # 3. Upcoming event (should be kept)
        event_upcoming = Event.objects.create(
            title="Upcoming Event",
            description="In the future",
            category="food",
            date=now + timedelta(hours=24),
            venue_name="Venue C",
            price=30.00,
            organizer=self.organizer,
            total_tickets=100,
            is_published=True
        )

        # Verify initial database state (3 events exist)
        self.assertEqual(Event.objects.count(), 3)

        # Call the public listing endpoint to trigger the get_queryset cleanup logic
        response = self.client.get(self.events_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify database state after query (the event older than 24h is deleted)
        self.assertEqual(Event.objects.count(), 2)
        self.assertFalse(Event.objects.filter(pk=event_old.pk).exists())
        self.assertTrue(Event.objects.filter(pk=event_recent.pk).exists())
        self.assertTrue(Event.objects.filter(pk=event_upcoming.pk).exists())
