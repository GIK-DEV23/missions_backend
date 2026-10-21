"""Keep the seeded system roles in step with the permission templates.

WHY THIS EXISTS
---------------
`users/migrations/0007_seed_default_roles.py` wrote its own inline permission
lists, which became a second vocabulary alongside
`authentication/permissions_list.py`. They drifted badly — the seeded `staff`
role held 11 permissions where `STAFF_PERMISSIONS` lists 75, and six seeded
names (`create_user`, `view_reports`, `export_data`,
`process_deletion_request`, `view_deletion_request`, `create_role`) match no
route and no template at all.

Nobody noticed because `require_permission` lets a superuser or admin through
before checking anything, and `has_role_type("admin", ...)` matches both
`admin` and `superadmin` by substring. `staff` and `executive` get no such
bypass, so they were held to the stale list: an executive could not list
anything, and a staff member could not list souls or work the report queue.

`missioner_template` partly self-heals, because `get_or_create_template_role`
runs `create_role`, which updates an existing role's permissions. The other
seeded roles never do: that helper creates `admin_template` / `staff_template`
/ `exec_template`, which are *different rows* from the seeded `admin` /
`staff` / `executive`, so nothing ever refreshed them.

`permissions_list.py` is the single source of truth. This module is the only
writer of the seeded roles, used by both the data migration and the
`sync_default_roles` management command, so adding a permission to a template
never again requires remembering to hand-edit a role.
"""

from typing import Dict, Iterable, List, Tuple

from authentication import permissions_list

#: Seeded role name -> the template that defines it.
#:
#: `superadmin` gets ALL_PERMISSIONS explicitly rather than the old `["*"]`
#: sentinel: nothing in `require_permission` understands a wildcard (it tests
#: `permission_tag in user_permissions`), so `["*"]` granted literally nothing
#: and only worked because the role name contains "admin" and bypasses.
DEFAULT_ROLE_TEMPLATES: Dict[str, Iterable[str]] = {
    "superadmin": permissions_list.SUPERUSER_PERMISSIONS,
    "admin": permissions_list.ADMIN_PERMISSIONS,
    "staff": permissions_list.STAFF_PERMISSIONS,
    "executive": permissions_list.EXEC_PERMISSIONS,
    "missioner_template": permissions_list.MISSIONER_PERMISSIONS,
}

DEFAULT_ROLE_DESCRIPTIONS: Dict[str, str] = {
    "superadmin": "Super administrator with full system access",
    "admin": "Administrator with full access to manage users and content",
    "staff": "Staff member with content and soul management access",
    "executive": "Executive user with reporting and oversight access",
    "missioner_template": "Template role for missioners (evangelists)",
}


def sync_default_roles(role_model) -> List[Tuple[str, int, int, bool]]:
    """Write the seeded system roles from their templates.

    Takes the Role model as an argument so a data migration can pass
    `apps.get_model(...)` (the historical model) while the management command
    passes the real one.

    Only the five roles named above are touched: a role an operator created by
    hand is left exactly as it is, since this cannot know what it was for.

    Returns one (name, before_count, after_count, created) tuple per role, for
    the command to report.
    """
    results: List[Tuple[str, int, int, bool]] = []

    for name, template in DEFAULT_ROLE_TEMPLATES.items():
        permissions = sorted(template)
        role, created = role_model.objects.get_or_create(
            name=name,
            defaults={
                "permissions": permissions,
                "description": DEFAULT_ROLE_DESCRIPTIONS.get(name, ""),
            },
        )
        before = 0 if created else len(role.permissions or [])

        if not created and list(role.permissions or []) != permissions:
            role.permissions = permissions
            # Leave an operator-edited description alone; only fill a blank one.
            if not role.description:
                role.description = DEFAULT_ROLE_DESCRIPTIONS.get(name, "")
            role.save(update_fields=["permissions", "description", "updated_at"])

        results.append((name, before, len(permissions), created))

    return results
