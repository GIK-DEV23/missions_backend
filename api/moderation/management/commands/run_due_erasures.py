"""Erase accounts whose grace period has elapsed.

Without this nothing ever carries out a deletion request: the API only records
the request and starts the clock. Run it on a schedule (daily is enough for a
30-day window):

    python manage.py run_due_erasures

Use --dry-run to see what it would erase and --limit to cap a single pass.
Accounts under legal hold are never selected, and each erasure is independent,
so one failure does not strand the rest.
"""

import logging

from django.core.management.base import BaseCommand

from base.utils.exceptions import ForbiddenError
from moderation.selectors import due_for_erasure
from moderation.services import perform_erasure

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Carry out account erasures whose 30-day grace period has elapsed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the accounts that are due without erasing anything.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Erase at most this many accounts in one pass (0 = no cap).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        due = due_for_erasure()
        if limit:
            due = due[:limit]
        due = list(due)

        if not due:
            self.stdout.write("No accounts are due for erasure.")
            return

        self.stdout.write(
            "{} account(s) due for erasure.".format(len(due))
            + (" (dry run)" if dry_run else "")
        )

        erased, failed = 0, 0
        for record in due:
            label = "user #{} (requested {})".format(
                record.user_id,
                record.requested_at.date().isoformat() if record.requested_at else "?",
            )
            if dry_run:
                self.stdout.write("  would erase {}".format(label))
                continue
            try:
                perform_erasure(record)
                erased += 1
                self.stdout.write(self.style.SUCCESS("  erased {}".format(label)))
            except ForbiddenError as e:
                # Expected when a hold was placed, or the clock was changed,
                # between the query and the write.
                failed += 1
                self.stdout.write(self.style.WARNING("  skipped {}: {}".format(label, e)))
            except Exception:
                failed += 1
                logger.exception("Erasure failed for user %s", record.user_id)
                self.stdout.write(self.style.ERROR("  FAILED {} (see logs)".format(label)))

        if not dry_run:
            self.stdout.write("Done: {} erased, {} skipped or failed.".format(erased, failed))
