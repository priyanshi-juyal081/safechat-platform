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
