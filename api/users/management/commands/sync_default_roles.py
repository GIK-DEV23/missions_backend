"""Re-sync the seeded system roles from the permission templates.

Run this after changing anything in `authentication/permissions_list.py`:

    python manage.py sync_default_roles

Without it a new permission is assignable in the dashboard's Roles page but
held by no existing role, so the endpoint requiring it is reachable only by an
admin or superuser (who bypass the check). Roles an operator created by hand
are never touched.

`--dry-run` reports what would change and writes nothing.
"""

from django.core.management.base import BaseCommand

from users.models import Role
from users.role_sync import DEFAULT_ROLE_TEMPLATES, sync_default_roles


class Command(BaseCommand):
    help = "Re-sync the seeded system roles from authentication/permissions_list.py"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write("Dry run — nothing will be written.\n")
            for name, template in DEFAULT_ROLE_TEMPLATES.items():
                want = sorted(template)
                role = Role.objects.filter(name=name).first()
                if role is None:
                    self.stdout.write(
                        "  {}: would CREATE with {} permission(s)".format(name, len(want))
                    )
                    continue
                have = list(role.permissions or [])
                if have == want:
                    self.stdout.write("  {}: already in sync ({})".format(name, len(want)))
                    continue
                missing = sorted(set(want) - set(have))
                extra = sorted(set(have) - set(want))
                self.stdout.write(
                    "  {}: {} -> {} permission(s); +{} missing, -{} stale".format(
                        name, len(have), len(want), len(missing), len(extra)
                    )
                )
                if missing:
                    self.stdout.write("      adding:   {}".format(", ".join(missing)))
                if extra:
                    self.stdout.write("      removing: {}".format(", ".join(extra)))
            return

        results = sync_default_roles(Role)
        for name, before, after, created in results:
            if created:
                self.stdout.write(
                    self.style.SUCCESS("  created {} with {} permission(s)".format(name, after))
                )
            elif before == after:
                self.stdout.write("  {} already in sync ({})".format(name, after))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "  synced {}: {} -> {} permission(s)".format(name, before, after)
                    )
                )
        self.stdout.write("Done. Custom roles were not touched.")
