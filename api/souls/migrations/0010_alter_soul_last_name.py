from django.db import migrations, models


class Migration(migrations.Migration):
    """Allow a blank last name so single-word soul names are accepted.

    ``last_name`` becomes optional at the validation level (blank=True) with an
    empty-string default. No column type change (CharField stays the same), so
    this is a metadata-only alteration.
    """

    dependencies = [
        ("souls", "0009_migrate_soul_assignments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="soul",
            name="last_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
