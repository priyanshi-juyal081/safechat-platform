from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Warning(models.Model):
    """User warning model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField()
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_warnings')
    is_automatic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Warning for {self.user.username} - {self.reason[:50]}"


class Restriction(models.Model):
    """User restriction/ban model"""
    RESTRICTION_TYPES = [
        ('chat', 'Chat Restriction'),
        ('stream', 'Stream Restriction'),
        ('full', 'Full Ban'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restrictions')
    restriction_type = models.CharField(max_length=10, choices=RESTRICTION_TYPES, default='chat')
    reason = models.TextField()
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_restrictions')
    is_permanent = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.restriction_type} for {self.user.username}"


class ToxicityLog(models.Model):
    """Log all toxicity detection attempts"""
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE)
    toxicity_score = models.FloatField()
    detected_categories = models.JSONField(default=dict)
    is_toxic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_toxic', '-created_at']),
        ]
    
    def __str__(self):
        return f"Toxicity: {self.toxicity_score:.2f} - {self.message.text[:50]}"


class SpeechViolation(models.Model):
    """Track speech violations during live streams"""
    # Allow nullable user for ephemeral / unauthenticated clients
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='speech_violations')
    # Store a raw identifier when no DB `User` exists (e.g. frontend ephemeral id)
    user_identifier = models.CharField(max_length=255, null=True, blank=True)
    # Allow nullable stream (frontend may not create Stream rows) and store raw identifier
    stream = models.ForeignKey('chat.Stream', on_delete=models.SET_NULL, null=True, blank=True, related_name='speech_violations')
    stream_identifier = models.CharField(max_length=255, null=True, blank=True)
    transcript = models.TextField()
    toxicity_score = models.FloatField()
    detected_words = models.JSONField(default=list)
    violation_type = models.CharField(max_length=20, choices=[
        ('warning', 'Warning'),
        ('timeout', 'Timeout'),
        ('stream_stop', 'Stream Stopped')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'stream', '-created_at']),
            models.Index(fields=['stream', '-created_at']),
        ]
    
    def __str__(self):
        user_display = self.user.username if self.user else (self.user_identifier or 'unknown')
        stream_display = self.stream.title if self.stream else (self.stream_identifier or 'unknown')
        return f"Speech violation by {user_display} in {stream_display}"


class StreamTimeout(models.Model):
    """Track stream timeouts for users"""
    # Allow nullable user for ephemeral / unauthenticated clients
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stream_timeouts')
    # Raw identifier when no DB `User` exists
    user_identifier = models.CharField(max_length=255, null=True, blank=True)
    # Allow nullable stream and raw identifier
    stream = models.ForeignKey('chat.Stream', on_delete=models.SET_NULL, null=True, blank=True, related_name='timeouts')
    stream_identifier = models.CharField(max_length=255, null=True, blank=True)
    duration_seconds = models.IntegerField(default=60)  # Default 1 minute timeout
    reason = models.TextField()
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'stream', 'is_active']),
        ]
    
    def __str__(self):
        user_display = self.user.username if self.user else (self.user_identifier or 'unknown')
        stream_display = self.stream.title if self.stream else (self.stream_identifier or 'unknown')
        return f"Timeout for {user_display} in {stream_display}"
