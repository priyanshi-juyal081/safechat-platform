from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Message(models.Model):
    """Chat message model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField(max_length=1000)
    stream = models.ForeignKey('Stream', on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    is_flagged = models.BooleanField(default=False)
    toxicity_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['stream', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}"


class Stream(models.Model):
    """Live stream model"""
    STATUS_CHOICES = [
        ('live', 'Live'),
        ('ended', 'Ended'),
        ('paused', 'Paused'),
    ]
    
    streamer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streams')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='live')
    viewer_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.streamer.username} - {self.title}"


class StreamViewer(models.Model):
    """Track viewers for each stream"""
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='viewers')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['stream', 'user']
        indexes = [
            models.Index(fields=['stream', 'joined_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} watching {self.stream.title}"
