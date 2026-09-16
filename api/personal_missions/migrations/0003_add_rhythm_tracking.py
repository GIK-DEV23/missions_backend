# Generated manually for rhythm tracking feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('personal_missions', '0002_alter_personalmission_rhythm_day'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalMissionPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('period_index', models.IntegerField(help_text='0-based index computed from mission start_date and rhythm')),
                ('period_start', models.DateField(help_text='First day of this period')),
                ('period_end', models.DateField(help_text='Last day of this period')),
                ('met_at', models.DateTimeField(help_text='When the period was marked as met')),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='met_periods', to='personal_missions.personalmission')),
            ],
            options={
                'db_table': 'personal_mission_periods',
            },
        ),
        migrations.CreateModel(
            name='PersonalMissionSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('date', models.DateField(help_text='Date of the session')),
                ('notes', models.TextField(blank=True, null=True)),
                ('souls_count', models.PositiveIntegerField(default=0, help_text='Number of souls won during this session')),
                ('duration_minutes', models.PositiveIntegerField(blank=True, help_text='Duration of the session in minutes', null=True)),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='personal_missions.personalmission')),
            ],
            options={
                'db_table': 'personal_mission_sessions',
            },
        ),
        migrations.AddIndex(
            model_name='personalmissionsession',
            index=models.Index(fields=['mission', 'date'], name='personal_mi_mission_a2c8e5_idx'),
        ),
        migrations.AddIndex(
            model_name='personalmissionperiod',
            index=models.Index(fields=['mission', 'period_index'], name='personal_mi_mission_f8d2a1_idx'),
        ),
        migrations.AddConstraint(
            model_name='personalmissionperiod',
            constraint=models.UniqueConstraint(fields=('mission', 'period_index'), name='unique_mission_period'),
        ),
    ]
