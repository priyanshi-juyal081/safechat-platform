from rest_framework import serializers
from .models import Message, Stream, StreamViewer
from users.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'user', 'username', 'text', 'stream', 'is_flagged', 'toxicity_score', 'created_at']
        read_only_fields = ['id', 'user', 'is_flagged', 'toxicity_score', 'created_at']


class StreamSerializer(serializers.ModelSerializer):
    streamer_name = serializers.CharField(source='streamer.username', read_only=True)
    
    class Meta:
        model = Stream
        fields = ['id', 'streamer', 'streamer_name', 'title', 'description', 'status', 'viewer_count', 'started_at', 'ended_at']
        read_only_fields = ['id', 'streamer', 'viewer_count', 'started_at', 'ended_at']


class StreamViewerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StreamViewer
        fields = ['id', 'stream', 'user', 'username', 'joined_at', 'left_at']
        read_only_fields = ['id', 'joined_at']

