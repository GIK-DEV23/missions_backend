"""Re-sync the seeded system roles from authentication/permissions_list.py.

Migration 0007 wrote its own inline permission lists, creating a second
vocabulary that drifted from the templates: the seeded `staff` role held 11
permissions where STAFF_PERMISSIONS lists 75, `executive` held 8 of 36, and six
seeded names matched no route and no template at all (`create_user`,
`view_reports`, `export_data`, `process_deletion_request`,
`view_deletion_request`, `create_role`).

That was invisible while `require_permission` was bypassed on 27 endpoints and
because admin/superadmin skip the check by role name. With the checks now
enforced, a `staff` or `executive` user is held to whatever the seed wrote, so
the grants have to be correct.

Deliberately imports `users.role_sync` rather than inlining the lists again —
inlining is what produced the drift, and a third copy would reproduce it. The
intent of this migration is "make the seeded roles match the templates as they
are now", so reading the current templates is the correct behaviour on replay.
Only the five seeded roles are touched; operator-created roles are untouched.
"""

from django.db import migrations

from users.role_sync import sync_default_roles


def forwards(apps, schema_editor):
    sync_default_roles(apps.get_model("users", "Role"))


def backwards(apps, schema_editor):
    """No-op.

    Reversing would mean restoring a permission set we know to be wrong, which
    would silently re-break staff and executive access. Rolling back past this
    point is therefore a data decision for an operator, not something to undo
    automatically.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_seed_default_roles"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
