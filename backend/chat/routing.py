from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<stream_id>\d+)/$', consumers.StreamChatConsumer.as_asgi()),
    re_path(r'ws/streams/$', consumers.StreamConsumer.as_asgi()),
]