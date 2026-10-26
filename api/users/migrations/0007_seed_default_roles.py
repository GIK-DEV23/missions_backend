# Generated manually - seed default system roles

from django.db import migrations


DEFAULT_ROLES = [
    {
        "name": "superadmin",
        "description": "Super administrator with full system access",
        "permissions": ["*"],  # All permissions
    },
    {
        "name": "admin",
        "description": "Administrator with full access to manage users and content",
        "permissions": [
            "view_user", "create_user", "update_user", "delete_user",
            "view_role", "create_role", "update_role", "delete_role",
            "view_soul", "create_soul", "update_soul", "delete_soul", "assign_soul",
            "view_mission", "create_mission", "update_mission", "delete_mission",
            "view_testimony", "approve_testimony", "reject_testimony",
            "view_miracle", "approve_miracle", "reject_miracle",
            "view_deletion_request", "process_deletion_request",
            "view_reports", "export_data",
        ],
    },
    {
        "name": "staff",
        "description": "Staff member with content moderation access",
        "permissions": [
            "view_user", "view_soul", "update_soul",
            "view_mission",
            "view_testimony", "approve_testimony", "reject_testimony",
            "view_miracle", "approve_miracle", "reject_miracle",
            "view_reports",
        ],
    },
    {
        "name": "executive",
        "description": "Executive user with reporting and oversight access",
        "permissions": [
            "view_user", "view_soul", "view_mission",
            "view_testimony", "view_miracle",
            "view_reports", "export_data",
            "view_deletion_request",
        ],
    },
    {
        "name": "missioner_template",
        "description": "Template role for missioners (evangelists)",
        "permissions": [
            "view_soul", "create_soul", "update_soul",
            "create_progress_update", "view_progress_update", "update_progress_update", "delete_progress_update",
            "create_testimony", "update_testimony",
            "create_miracle", "update_miracle",
        ],
    },
]


def seed_roles(apps, schema_editor):
    """Create default system roles if they don't exist."""
    Role = apps.get_model("users", "Role")
    
    for role_data in DEFAULT_ROLES:
        Role.objects.update_or_create(
            name=role_data["name"],
            defaults={
                "description": role_data["description"],
                "permissions": role_data["permissions"],
                "is_archived": False,
            }
        )


def reverse_seed_roles(apps, schema_editor):
    """Remove seeded roles (except missioner_template which may have users)."""
    Role = apps.get_model("users", "Role")
    # Only remove the newly added roles, keep missioner_template
    Role.objects.filter(name__in=["superadmin", "admin", "staff", "executive"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_alter_user_profile_photo"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_seed_roles),
    ]
