"""Restore phone-conditional uniqueness on Soul.

Migration 0013 made phone_number nullable for minors and, in doing so, replaced
the key (first_name, last_name, phone_number, user, mission) with
(first_name, last_name, user, mission). That is STRICTLY TIGHTER: the phone was
the field distinguishing two people who share a name, so the second "John Doe"
an evangelist recorded on a mission was rejected even when the two had
different numbers.

This drops that key and adds a partial unique index that applies only when a
phone is present — restoring the original behaviour for souls that have one,
and imposing no uniqueness on those that do not, which is where minors now sit
by design.

Safe to apply to existing data: between 0013 and here the key was tighter than
the one being restored, so no row can violate it. The one exception is a
phone_number stored as an empty string rather than NULL, which would fall
inside the partial condition and could collide; those are normalised to NULL
first. No current write path produces '' (the clients send null and
upload_souls returns None for minors), so this is belt-and-braces for rows
predating that.

NOT CLEANLY REVERSIBLE once the fix has been used, and that is the bug
demonstrating itself: reversing re-adds the (first_name, last_name, user,
mission) key, which cannot hold two same-named souls distinguished by phone —
exactly the records this migration makes possible. Rolling back therefore
requires deciding what to do with those rows, so it is an operator decision
rather than an automatic one.
"""

from django.conf import settings
from django.db import migrations, models


def blank_phones_to_null(apps, schema_editor):
    """An empty phone is no phone. Keeps it out of the partial unique index."""
    Soul = apps.get_model("souls", "Soul")
    Soul.objects.filter(phone_number="").update(phone_number=None)


def noop(apps, schema_editor):
    """Nothing to restore: '' and NULL both mean "no phone recorded"."""


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0009_alter_mission_banner_image_alter_mission_status_and_more'),
        ('personal_missions', '0003_add_rhythm_tracking'),
        ('souls', '0013_phone_number_optional_for_minors'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(blank_phones_to_null, noop),
        migrations.AlterUniqueTogether(
            name='soul',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='soul',
            constraint=models.UniqueConstraint(
                condition=models.Q(('phone_number__isnull', False)),
                fields=('first_name', 'last_name', 'phone_number', 'user', 'mission'),
                name='uniq_soul_name_phone_user_mission_when_phone_set',
            ),
        ),
    ]
