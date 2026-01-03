from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_restricted', 'created_at']
    list_filter = ['is_restricted', 'is_staff', 'is_superuser']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('bio', 'avatar', 'is_restricted', 'restriction_reason', 'restricted_at')}),
    )