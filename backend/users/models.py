from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Extended User model with additional fields for moderation and social features"""
    nickname = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Behavioral stats
    toxicity_score = models.FloatField(default=0.0, help_text="Average toxicity score (0-1)")
    messages_blocked = models.IntegerField(default=0, help_text="Number of toxic messages blocked")
    messages_sent = models.IntegerField(default=0, help_text="Total number of messages sent")
    fake_news_count = models.IntegerField(default=0, help_text="Number of fake news posts detected")
    reports_received = models.IntegerField(default=0, help_text="Number of times this user was reported")
    
    # Social features
    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True
    )
    
    # Restriction fields
    is_restricted = models.BooleanField(default=False)
    restriction_reason = models.TextField(blank=True)
    restricted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix the clash by adding related_name (required when extending AbstractUser)
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_permissions',
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()