import json
import time
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Stream
from moderation.ai_detector import ToxicityDetector
from asgiref.sync import sync_to_async


@database_sync_to_async
def get_or_create_user_db(username, client_user_id=None):
    User = get_user_model()
    try:
        if client_user_id:
            u = User.objects.filter(id=client_user_id).first()
            if u:
                return u.id
    except Exception:
        pass

    user, _ = User.objects.get_or_create(username=username)
    return user.id

class ChatConsumer(AsyncWebsocketConsumer):
    """Global chat WebSocket consumer"""
    
    async def connect(self):
        self.room_group_name = 'global_chat'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send recent messages
        messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': messages
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                username = data.get('username')
                message_text = data.get('message')
                client_user_id = data.get('user_id')

                # Resolve or create a server-side user for this client (ensures restriction checks work)
                server_user_id = await get_or_create_user_db(username, client_user_id)

                # Check if user is restricted (using server-side id)
                is_restricted = await self.check_user_restriction(server_user_id)
                if is_restricted:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'You are restricted from chatting'
                    }))
                    return

                # Check toxicity (ASYNC, no database_sync_to_async wrapper)
                detector = ToxicityDetector()
                toxicity_result = await detector.analyze_async(message_text)

                is_toxic = toxicity_result['is_toxic']
                toxicity_score = toxicity_result['toxicity_score']

                if is_toxic:
                    # Increment messages_sent and messages_blocked for the user
                    await self.increment_user_stat(server_user_id, 'messages_sent')
                    await self.increment_user_stat(server_user_id, 'messages_blocked')
                    
                    # Do not save or broadcast toxic messages; issue a warning and possibly restrict
                    warning_count = await self.issue_warning(server_user_id, None)
                    if warning_count >= 3:
                        await self.restrict_user(server_user_id)
                        await self.send(text_data=json.dumps({
                            'type': 'restriction',
                            'message': 'You have been restricted from chatting due to repeated violations'
                        }))
                    else:
                        await self.send(text_data=json.dumps({
                            'type': 'warning',
                            'warning_count': warning_count,
                            'message': f'Warning {warning_count}/3: Your message contains inappropriate content'
                        }))
                    return

                # Increment messages_sent for the user
                await self.increment_user_stat(server_user_id, 'messages_sent')

                # Save non-toxic message to database and broadcast
                message = await self.save_message(
                    server_user_id,
                    message_text,
                    None,
                    is_toxic,
                    toxicity_score
                )

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message
                    }
                )
        except Exception:
            traceback.print_exc()
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Server error processing message'
                }))
            except:
                pass
    
    async def chat_message(self, event):
        """Receive message from room group"""
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }))
    
    @database_sync_to_async
    def get_recent_messages(self):
        messages = Message.objects.filter(stream=None).select_related('user').order_by('-created_at')[:50]
        return [{
            'id': msg.id,
            'user_id': msg.user.id,
            'username': msg.user.username,
            'text': msg.text,
            'is_flagged': msg.is_flagged,
            'toxicity_score': msg.toxicity_score,
            'timestamp': msg.created_at.isoformat(),
        } for msg in reversed(messages)]
    
    @database_sync_to_async
    def increment_user_stat(self, user_id, field):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            current_val = getattr(user, field, 0)
            setattr(user, field, current_val + 1)
            user.save()
            print(f"   [+] Stats: Incremented {field} for user {user.username}")
        except Exception as e:
            print(f"   [!] Stats Error: {e}")

    @database_sync_to_async
    def save_message(self, user_id, text, stream_id, is_flagged, toxicity_score):
        try:
            User = get_user_model()
            user = User.objects.get(id=user_id)
        except Exception:
            # Create a lightweight guest user when the provided user_id doesn't exist
            username = f'guest_{user_id or int(time.time()*1000)}'
            User = get_user_model()
            user, _ = User.objects.get_or_create(username=username)
        stream = Stream.objects.get(id=stream_id) if stream_id else None
        
        message = Message.objects.create(
            user=user,
            text=text,
            stream=stream,
            is_flagged=is_flagged,
            toxicity_score=toxicity_score
        )
        
        return {
            'id': message.id,
            'user_id': message.user.id,
            'username': message.user.username,
            'text': message.text,
            'is_flagged': message.is_flagged,
            'toxicity_score': message.toxicity_score,
            'timestamp': message.created_at.isoformat(),
        }
    
    @database_sync_to_async
    def check_user_restriction(self, user_id):
        if not user_id:
            return False
        try:
            from moderation.models import Restriction
            from django.utils import timezone
            
            restrictions = Restriction.objects.filter(
                user_id=user_id,
                restriction_type__in=['chat', 'full']
            ).filter(
                is_permanent=True
            ) | Restriction.objects.filter(
                user_id=user_id,
                restriction_type__in=['chat', 'full'],
                expires_at__gt=timezone.now()
            )
            
            return restrictions.exists()
        except:
            return False

    
    
    @database_sync_to_async
    def issue_warning(self, user_id, message_id):
        from moderation.models import Warning
        User = get_user_model()
        user = User.objects.get(id=user_id)
        message = Message.objects.get(id=message_id) if message_id else None

        Warning.objects.create(
            user=user,
            message=message,
            reason="Automatic: Toxic content detected",
            is_automatic=True
        )

        return Warning.objects.filter(user=user).count()
    
    @database_sync_to_async
    def restrict_user(self, user_id):
        from moderation.models import Restriction
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        Restriction.objects.create(
            user=user,
            restriction_type='chat',
            reason="Automatic: 3 warnings for toxic behavior",
            is_permanent=False
        )


class StreamChatConsumer(AsyncWebsocketConsumer):
    """Stream-specific chat WebSocket consumer"""
    
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'stream_chat_{self.stream_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update viewer count
        await self.update_viewer_count(1)
        
        # Send recent messages
        messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': messages
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update viewer count
        await self.update_viewer_count(-1)
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                username = data.get('username')
                message_text = data.get('message')
                client_user_id = data.get('user_id')

                # Resolve or create a server-side user for this client (ensures restriction checks work)
                server_user_id = await get_or_create_user_db(username, client_user_id)

                # Check if user is restricted (using server-side id)
                is_restricted = await self.check_user_restriction(server_user_id)
                if is_restricted:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'You are restricted from chatting'
                    }))
                    return

                # Check toxicity (ASYNC)
                detector = ToxicityDetector()
                toxicity_result = await detector.analyze_async(message_text)

                is_toxic = toxicity_result['is_toxic']
                toxicity_score = toxicity_result['toxicity_score']

                if is_toxic:
                    # Increment messages_sent and messages_blocked for the user
                    await self.increment_user_stat(server_user_id, 'messages_sent')
                    await self.increment_user_stat(server_user_id, 'messages_blocked')
                    
                    # Issue warning without saving the message and don't broadcast
                    warning_count = await self.issue_warning(server_user_id, None)
                    if warning_count >= 3:
                        await self.restrict_user(server_user_id)
                        await self.send(text_data=json.dumps({
                            'type': 'restriction',
                            'message': 'You have been restricted from chatting'
                        }))
                    else:
                        await self.send(text_data=json.dumps({
                            'type': 'warning',
                            'warning_count': warning_count,
                            'message': f'Warning {warning_count}/3: Inappropriate content'
                        }))
                    return

                # Increment messages_sent for the user
                await self.increment_user_stat(server_user_id, 'messages_sent')

                # Save non-toxic message to database and broadcast
                message = await self.save_message(
                    server_user_id,
                    message_text,
                    self.stream_id,
                    is_toxic,
                    toxicity_score
                )

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message
                    }
                )
        except Exception:
            traceback.print_exc()
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Server error processing message'
                }))
            except:
                pass
    
    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }))
    
    @database_sync_to_async
    def get_recent_messages(self):
        messages = Message.objects.filter(
            stream_id=self.stream_id
        ).select_related('user').order_by('-created_at')[:50]
        
        return [{
            'id': msg.id,
            'user_id': msg.user.id,
            'username': msg.user.username,
            'text': msg.text,
            'is_flagged': msg.is_flagged,
            'toxicity_score': msg.toxicity_score,
            'timestamp': msg.created_at.isoformat(),
        } for msg in reversed(messages)]
    
    @database_sync_to_async
    def increment_user_stat(self, user_id, field):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            current_val = getattr(user, field, 0)
            setattr(user, field, current_val + 1)
            user.save()
        except:
            pass

    @database_sync_to_async
    def save_message(self, user_id, text, stream_id, is_flagged, toxicity_score):
        try:
            User = get_user_model()
            user = User.objects.get(id=user_id)
        except Exception:
            username = f'guest_{user_id or int(time.time()*1000)}'
            User = get_user_model()
            user, _ = User.objects.get_or_create(username=username)
        stream = Stream.objects.get(id=stream_id)
        
        message = Message.objects.create(
            user=user,
            text=text,
            stream=stream,
            is_flagged=is_flagged,
            toxicity_score=toxicity_score
        )
        
        return {
            'id': message.id,
            'user_id': message.user.id,
            'username': message.user.username,
            'text': message.text,
            'is_flagged': message.is_flagged,
            'toxicity_score': message.toxicity_score,
            'timestamp': message.created_at.isoformat(),
        }
    
    @database_sync_to_async
    def update_viewer_count(self, change):
        try:
            stream = Stream.objects.get(id=self.stream_id)
            stream.viewer_count = max(0, stream.viewer_count + change)
            stream.save()
        except Stream.DoesNotExist:
            pass
    
    @database_sync_to_async
    def check_user_restriction(self, user_id):
        if not user_id:
            return False
        try:
            from moderation.models import Restriction
            from django.utils import timezone
            
            restrictions = Restriction.objects.filter(
                user_id=user_id,
                restriction_type__in=['chat', 'full']
            ).filter(
                is_permanent=True
            ) | Restriction.objects.filter(
                user_id=user_id,
                restriction_type__in=['chat', 'full'],
                expires_at__gt=timezone.now()
            )
            
            return restrictions.exists()
        except:
            return False
    
    @database_sync_to_async
    def issue_warning(self, user_id, message_id):
        from moderation.models import Warning
        User = get_user_model()
        user = User.objects.get(id=user_id)
        message = Message.objects.get(id=message_id) if message_id else None

        Warning.objects.create(
            user=user,
            message=message,
            reason="Automatic: Toxic content detected",
            is_automatic=True
        )

        return Warning.objects.filter(user=user).count()
    
    @database_sync_to_async
    def restrict_user(self, user_id):
        from moderation.models import Restriction
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        Restriction.objects.create(
            user=user,
            restriction_type='chat',
            reason="Automatic: warnings for toxic behavior",
            is_permanent=False
        )


class StreamConsumer(AsyncWebsocketConsumer):
    """Live stream status updates"""
    
    async def connect(self):
        self.room_group_name = 'streams'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current streams
        streams = await self.get_active_streams()
        await self.send(text_data=json.dumps({
            'type': 'stream_list',
            'streams': streams
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'stream_update':
            # Broadcast stream update
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'stream_update',
                    'stream': data['stream']
                }
            )
    
    async def stream_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'stream_update',
            'stream': event['stream']
        }))
    
    @database_sync_to_async
    def get_active_streams(self):
        streams = Stream.objects.filter(status='live').select_related('streamer')
        return [{
            'id': stream.id,
            'streamer_id': stream.streamer.id,
            'streamer_name': stream.streamer.username,
            'title': stream.title,
            'viewer_count': stream.viewer_count,
            'started_at': stream.started_at.isoformat(),
        } for stream in streams]