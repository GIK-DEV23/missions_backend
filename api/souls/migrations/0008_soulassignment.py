from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('souls', '0007_soul_consent_given_soul_consent_recorded_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SoulAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_souls', to=settings.AUTH_USER_MODEL)),
                ('soul', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='souls.soul')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='soul_assignments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'soul_assignments',
            },
        ),
        migrations.AddIndex(
            model_name='soulassignment',
            index=models.Index(fields=['soul', 'is_active'], name='soul_assign_soul_id_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='soulassignment',
            index=models.Index(fields=['user', 'is_active'], name='soul_assign_user_id_d4e5f6_idx'),
        ),
    ]
