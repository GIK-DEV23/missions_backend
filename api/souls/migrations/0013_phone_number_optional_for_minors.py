# Generated manually for child-safety data minimisation
# Phone number is now optional, especially for minors (age 0-17)

from django.db import migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('souls', '0012_soul_guardian_consent_fields'),
    ]

    operations = [
        # Make phone_number nullable
        migrations.AlterField(
            model_name='soul',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True,
                null=True,
                max_length=128,
                region=None,
                help_text='Optional for minors (age 0-17) per child-safety data minimisation',
            ),
        ),
        # Remove phone_number from unique constraint
        # Old: ('first_name', 'last_name', 'phone_number', 'user', 'mission')
        # New: ('first_name', 'last_name', 'user', 'mission')
        migrations.AlterUniqueTogether(
            name='soul',
            unique_together={('first_name', 'last_name', 'user', 'mission')},
        ),
    ]
