from django.contrib import admin
from .models import Warning, Restriction, ToxicityLog

@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = ['user', 'reason_preview', 'is_automatic', 'created_at']
    list_filter = ['is_automatic', 'created_at']
    search_fields = ['user__username', 'reason']
    
    def reason_preview(self, obj):
        return obj.reason[:50]

@admin.register(Restriction)
class RestrictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'restriction_type', 'is_permanent', 'expires_at', 'created_at']
    list_filter = ['restriction_type', 'is_permanent', 'created_at']
    search_fields = ['user__username', 'reason']

@admin.register(ToxicityLog)
class ToxicityLogAdmin(admin.ModelAdmin):
    list_display = ['message_preview', 'toxicity_score', 'is_toxic', 'created_at']
    list_filter = ['is_toxic', 'created_at']
    
    def message_preview(self, obj):
        return obj.message.text[:50]