from rest_framework import serializers
from .models import Warning, Restriction, ToxicityLog

class WarningSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Warning
        fields = ['id', 'user', 'username', 'message', 'reason', 'issued_by', 'is_automatic', 'created_at']
        read_only_fields = ['id', 'created_at']


class RestrictionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Restriction
        fields = ['id', 'user', 'username', 'restriction_type', 'reason', 'issued_by', 'is_permanent', 'expires_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class ToxicityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToxicityLog
        fields = ['id', 'message', 'toxicity_score', 'detected_categories', 'is_toxic', 'created_at']
        read_only_fields = ['id', 'created_at']

