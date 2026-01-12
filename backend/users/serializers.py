from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'date_joined', 'nickname', 'bio', 'avatar',
            'toxicity_score', 'messages_blocked', 'messages_sent', 'fake_news_count', 
            'reports_received', 'followers_count', 'following_count', 'is_restricted'
        ]
        read_only_fields = [
            'id', 'date_joined', 'toxicity_score', 'messages_blocked', 
            'messages_sent', 'fake_news_count', 'reports_received', 
            'followers_count', 'following_count'
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user