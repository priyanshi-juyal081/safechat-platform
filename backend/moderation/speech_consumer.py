import json
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from chat.models import Stream
from moderation.models import SpeechViolation, StreamTimeout
from moderation.ai_detector import ToxicityDetector
from asgiref.sync import sync_to_async


# Run the possibly-blocking moderation call in a threadpool
@sync_to_async
def run_moderation(text: str):
    # Prefer OpenAI by default; allow overriding with MODERATION_METHOD env var
    method = os.getenv('MODERATION_METHOD', 'api')
    detector = ToxicityDetector(method=method)
    result = detector.analyze(text)
    # Log which method was used so behavior is easier to debug
    print(f"run_moderation using method={method} -> {result.get('method')}")
    return result


class SpeechModerationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time speech moderation"""
    
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'speech_moderation_{self.stream_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
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

            if message_type == 'speech_transcript':
                try:
                    transcript = data.get('transcript', '').strip()
                    user_id = data.get('user_id')
                    stream_id = data.get('stream_id')

                    if not transcript:
                        return

                    # Run moderation in a threadpool-safe manner
                    result = await run_moderation(transcript)

                    # Debug: log moderation result to server stdout for troubleshooting
                    print(f"MODERATION RESULT for user {user_id}: {result}")

                    if result.get('is_toxic'):
                        # Send toxic response to client (frontend can log to browser console)
                        await self.send(text_data=json.dumps({
                            'type': 'speech_toxic',
                            'transcript': transcript,
                            'details': result
                        }))

                        # Try to persist/log the violation, but don't let DB errors break moderation
                        try:
                            # Get existing violation count for this user/stream and increment
                            current_count = await self.get_violation_count(user_id, stream_id)
                            new_count = (current_count or 0) + 1

                            # Log the violation with the new count
                            await self.log_violation(
                                user_id,
                                stream_id,
                                transcript,
                                result.get('toxicity_score', 0),
                                result.get('detected_words', []),
                                new_count
                            )

                            # Notify client and take action based on the new violation count
                            if new_count == 1:
                                # First automatic warning
                                await self.send(text_data=json.dumps({
                                    'type': 'speech_warning',
                                    'warning_number': new_count,
                                    'message': f'Automatic warning ({new_count}/3) for speech violation'
                                }))
                            elif new_count == 2:
                                # Issue a timeout and notify client
                                timeout_seconds = 60
                                await self.issue_timeout(user_id, stream_id, timeout_seconds)
                                await self.send(text_data=json.dumps({
                                    'type': 'speech_timeout',
                                    'warning_number': new_count,
                                    'timeout_duration': timeout_seconds,
                                    'message': f'You have been timed out for {timeout_seconds} seconds due to repeated violations'
                                }))
                            elif new_count >= 3:
                                # Stop the stream and notify clients
                                await self.stop_stream(stream_id)
                                await self.send(text_data=json.dumps({
                                    'type': 'stream_stopped',
                                    'reason': 'Repeated speech violations',
                                    'message': 'Stream stopped due to repeated speech violations'
                                }))

                        except Exception as db_e:
                            # swallow DB errors to avoid breaking the WS
                            print('Error logging violation or enforcing action:', db_e)

                    else:
                        await self.send(text_data=json.dumps({
                            'type': 'speech_clean',
                            'transcript': transcript
                        }))

                except Exception as inner_e:
                    print('SPEECH MODERATION ERROR:', inner_e)
                    try:
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'message': 'Error processing speech'
                        }))
                    except Exception:
                        pass

        except Exception as e:
            print(f"Error in speech moderation receive loop: {e}")
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Error processing speech'
                }))
            except Exception:
                pass
    
    async def user_timeout_notification(self, event):
        """Notify about user timeout"""
        await self.send(text_data=json.dumps({
            'type': 'user_timed_out',
            'user_id': event['user_id'],
            'duration': event['duration']
        }))
    
    async def stream_stopped_notification(self, event):
        """Notify about stream being stopped"""
        await self.send(text_data=json.dumps({
            'type': 'stream_stopped',
            'reason': event['reason']
        }))
    
    @database_sync_to_async
    def get_violation_count(self, user_id, stream_id):
        """Get the number of violations for user in this stream"""
        return SpeechViolation.objects.filter(
            user_id=user_id,
            stream_id=stream_id
        ).count()
    
    @database_sync_to_async
    def log_violation(self, user_id, stream_id, transcript, toxicity_score, detected_words, violation_count):
        """Log a speech violation"""
        violation_type = 'warning'
        if violation_count == 2:
            violation_type = 'timeout'
        elif violation_count >= 3:
            violation_type = 'stream_stop'
        
        SpeechViolation.objects.create(
            user_id=user_id,
            stream_id=stream_id,
            transcript=transcript,
            toxicity_score=toxicity_score,
            detected_words=detected_words,
            violation_type=violation_type
        )
    
    @database_sync_to_async
    def issue_timeout(self, user_id, stream_id, duration_seconds):
        """Issue a timeout for the user"""
        expires_at = timezone.now() + timedelta(seconds=duration_seconds)
        
        StreamTimeout.objects.create(
            user_id=user_id,
            stream_id=stream_id,
            duration_seconds=duration_seconds,
            reason="Automatic: Speech violation timeout",
            expires_at=expires_at,
            is_active=True
        )
    
    @database_sync_to_async
    def check_timeout(self, user_id, stream_id):
        """Check if user is currently timed out"""
        active_timeout = StreamTimeout.objects.filter(
            user_id=user_id,
            stream_id=stream_id,
            is_active=True,
            expires_at__gt=timezone.now()
        ).exists()
        
        return active_timeout
    
    @database_sync_to_async
    def stop_stream(self, stream_id):
        """Stop the stream"""
        try:
            stream = Stream.objects.get(id=stream_id)
            stream.status = 'ended'
            stream.ended_at = timezone.now()
            stream.save()
        except Stream.DoesNotExist:
            pass