from django.contrib import admin
from .models import Message, Stream, StreamViewer

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'text_preview', 'is_flagged', 'toxicity_score', 'created_at']
    list_filter = ['is_flagged', 'created_at']
    search_fields = ['text', 'user__username']
    
    def text_preview(self, obj):
        return obj.text[:50]

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ['streamer', 'title', 'status', 'viewer_count', 'started_at']
    list_filter = ['status', 'started_at']
    search_fields = ['title', 'streamer__username']

@admin.register(StreamViewer)
class StreamViewerAdmin(admin.ModelAdmin):
    list_display = ['user', 'stream', 'joined_at', 'left_at']