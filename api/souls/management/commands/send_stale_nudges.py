from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification
from souls.constants import FollowUpHealth
from souls.models import Soul
from souls.selectors import compute_follow_up_health


class Command(BaseCommand):
    help = "Send nudge notifications for users with overdue or dormant soul follow-ups"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without creating notifications',
        )
        parser.add_argument(
            '--include-due',
            action='store_true',
            help='Also include souls that are "due" (not just overdue/dormant)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        include_due = options['include_due']

        target_health_states = [FollowUpHealth.OVERDUE, FollowUpHealth.DORMANT]
        if include_due:
            target_health_states.insert(0, FollowUpHealth.DUE)

        souls = Soul.objects.filter(
            deleted_at__isnull=True,
            do_not_contact=False,
            user__isnull=False,
        ).select_related('user')

        user_souls = {}
        for soul in souls:
            health = compute_follow_up_health(soul)
            if health in target_health_states:
                user_souls.setdefault(soul.user_id, []).append((soul, health))

        notifications_created = 0
        for user_id, soul_data in user_souls.items():
            overdue_count = sum(1 for _, h in soul_data if h == FollowUpHealth.OVERDUE)
            dormant_count = sum(1 for _, h in soul_data if h == FollowUpHealth.DORMANT)
            due_count = sum(1 for _, h in soul_data if h == FollowUpHealth.DUE)

            parts = []
            if due_count:
                parts.append("{} due".format(due_count))
            if overdue_count:
                parts.append("{} overdue".format(overdue_count))
            if dormant_count:
                parts.append("{} dormant".format(dormant_count))

            title = "Follow-up reminder"
            body = "You have {} for follow-up.".format(", ".join(parts))

            user = soul_data[0][0].user

            if dry_run:
                self.stdout.write(
                    "Would notify {} (ID {}): {}".format(user.email, user_id, body)
                )
            else:
                Notification.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    type="stale_followup_nudge",
                )
                notifications_created += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry run complete. {} users would be notified.".format(len(user_souls))
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Created {} notifications.".format(notifications_created)
            ))
