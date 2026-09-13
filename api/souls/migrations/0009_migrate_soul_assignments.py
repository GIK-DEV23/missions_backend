from django.db import migrations


def migrate_soul_users_to_assignments(apps, schema_editor):
    Soul = apps.get_model('souls', 'Soul')
    SoulAssignment = apps.get_model('souls', 'SoulAssignment')
    
    souls_with_users = Soul.objects.filter(user__isnull=False, deleted_at__isnull=True)
    
    assignments = [
        SoulAssignment(
            soul=soul,
            user=soul.user,
            assigned_by=None,
            is_active=True,
            notes="Migrated from legacy Soul.user field"
        )
        for soul in souls_with_users
    ]
    
    SoulAssignment.objects.bulk_create(assignments, batch_size=1000)


def reverse_migration(apps, schema_editor):
    SoulAssignment = apps.get_model('souls', 'SoulAssignment')
    SoulAssignment.objects.filter(notes="Migrated from legacy Soul.user field").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('souls', '0008_soulassignment'),
    ]

    operations = [
        migrations.RunPython(migrate_soul_users_to_assignments, reverse_migration),
    ]
