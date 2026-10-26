from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testimonies', '0006_highlight'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnonymousSubmissionToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_token_hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('submission_count', models.PositiveIntegerField(default=0)),
                ('window_start', models.DateTimeField(auto_now_add=True)),
                ('last_submission_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'anonymous_submission_tokens',
            },
        ),
    ]
