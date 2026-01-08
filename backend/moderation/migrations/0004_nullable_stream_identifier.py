"""Make moderation stream FK nullable and add stream_identifier fields.

Generated manually to support ephemeral frontend stream identifiers.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('moderation', '0003_nullable_user_identifier'),
        ('chat', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Alter SpeechViolation.stream to SET_NULL
        migrations.AlterField(
            model_name='speechviolation',
            name='stream',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='speech_violations', to='chat.stream'),
        ),

        # Add stream_identifier to SpeechViolation
        migrations.AddField(
            model_name='speechviolation',
            name='stream_identifier',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),

        # Alter StreamTimeout.stream to SET_NULL
        migrations.AlterField(
            model_name='streamtimeout',
            name='stream',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='timeouts', to='chat.stream'),
        ),

        # Add stream_identifier to StreamTimeout
        migrations.AddField(
            model_name='streamtimeout',
            name='stream_identifier',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
