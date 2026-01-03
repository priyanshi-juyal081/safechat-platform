"""
Fixed User Model with proper related_name
FILE: backend/users/models.py
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Extended User model with additional fields"""
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_restricted = models.BooleanField(default=False)
    restriction_reason = models.TextField(blank=True)
    restricted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix the clash by adding related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',  # Changed from user_set
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',  # Changed from user_set
        related_query_name='custom_user',
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username