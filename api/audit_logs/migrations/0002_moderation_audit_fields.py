# Generated manually for moderation audit trail

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit_logs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='content_type',
            field=models.CharField(
                blank=True,
                choices=[('testimony', 'Testimony'), ('miracle', 'Miracle')],
                help_text='Type of content being moderated (testimony, miracle)',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='content_id',
            field=models.IntegerField(
                blank=True,
                help_text='ID of the content being moderated',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='previous_status',
            field=models.CharField(
                blank=True,
                help_text='Status before this moderation action',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='new_status',
            field=models.CharField(
                blank=True,
                help_text='Status after this moderation action',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='rejection_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason for rejection (if action_type is REJECT)',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['content_type', 'content_id'], name='audit_logs_content_4f1234_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action_type', 'action_category'], name='audit_logs_action__8e5678_idx'),
        ),
    ]
