"""Make moderation user FK nullable and add user_identifier fields.

Generated manually to support ephemeral frontend user identifiers.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('moderation', '0002_speechviolation_streamtimeout'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Alter SpeechViolation.user to SET_NULL
        migrations.AlterField(
            model_name='speechviolation',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='speech_violations', to=settings.AUTH_USER_MODEL),
        ),

        # Add user_identifier to SpeechViolation
        migrations.AddField(
            model_name='speechviolation',
            name='user_identifier',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),

        # Alter StreamTimeout.user to SET_NULL
        migrations.AlterField(
            model_name='streamtimeout',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stream_timeouts', to=settings.AUTH_USER_MODEL),
        ),

        # Add user_identifier to StreamTimeout
        migrations.AddField(
            model_name='streamtimeout',
            name='user_identifier',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
