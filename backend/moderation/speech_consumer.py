import json
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from chat.models import Stream
from moderation.models import SpeechViolation, StreamTimeout
from moderation.ai_detector import ToxicityDetector, KeywordDetector
from asgiref.sync import sync_to_async


# Run the moderation call asynchronously
async def run_moderation_async(text: str):
    """Run moderation using the unified ToxicityDetector (consistent with chat)"""
    detector = ToxicityDetector()
    return await detector.analyze_async(text)


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
        print(f"✅ Speech moderation connected: Stream {self.stream_id}, User {self.user_id}")
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"❌ Speech moderation disconnected: Stream {self.stream_id}, User {self.user_id}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'speech_transcript':
                transcript = data.get('transcript', '').strip()
                user_id = data.get('user_id')
                stream_id = data.get('stream_id')

                if not transcript:
                    return

                print(f"\n🎤 Received transcript from user {user_id}: '{transcript}'")

                # Check if user is currently timed out
                is_timed_out = await self.check_timeout(user_id, stream_id)
                if is_timed_out:
                    print(f"⏸️  User {user_id} is timed out, ignoring speech")
                    await self.send(text_data=json.dumps({
                        'type': 'timeout_active',
                        'message': 'You are currently timed out and cannot speak'
                    }))
                    return

                # Run moderation using unified detector (Async)
                print(f"🔍 Running moderation on: '{transcript}'")
                result = await run_moderation_async(transcript)

                if result.get('is_toxic'):
                    # Get masked transcript
                    masked_transcript = result.get('masked_text', transcript)

                    if result.get('should_warn', True):
                        print(f"🚨 TOXIC SPEECH DETECTED (WARN)!")
                        # Get current violation count
                        current_count = await self.get_violation_count(user_id, stream_id)
                        new_count = current_count + 1
                        
                        # Log the violation
                        await self.log_violation(
                            user_id,
                            stream_id,
                            transcript,
                            result.get('toxicity_score', 0),
                            result.get('detected_words', []),
                            new_count
                        )

                        toxic_payload = {
                            'type': 'speech_toxic',
                            'transcript': masked_transcript,
                            'original_transcript': transcript,
                            'details': result,
                            'warning_number': new_count
                        }
                        await self.send(text_data=json.dumps(toxic_payload, default=str))

                        # Actions
                        if new_count == 1:
                            await self.send(text_data=json.dumps({'type': 'speech_warning', 'warning_number': 1, 'message': '⚠️ WARNING 1/3: Inappropriate content.'}, default=str))
                        elif new_count == 2:
                            timeout_seconds = 10
                            await self.issue_timeout(user_id, stream_id, timeout_seconds)
                            asyncio.create_task(self._schedule_timeout_expiry(user_id, stream_id, timeout_seconds))
                            await self.send(text_data=json.dumps({'type': 'speech_timeout', 'warning_number': 2, 'timeout_duration': timeout_seconds, 'message': f'🔇 muted for {timeout_seconds}s'}, default=str))
                        elif new_count >= 3:
                            await self.stop_stream(stream_id)
                            await self.send(text_data=json.dumps({'type': 'stream_stopped', 'message': '🚫 Stream terminated'}, default=str))
                    else:
                        print(f"✅ Speech has profanity but positive sentiment. Sending masked version only.")
                        await self.send(text_data=json.dumps({
                            'type': 'speech_clean', # Use speech_clean to avoid triggering UI warnings
                            'transcript': masked_transcript,
                            'is_masked': True
                        }))

                else:
                    print(f"✅ Speech is clean")
                    await self.send(text_data=json.dumps({
                        'type': 'speech_clean',
                        'transcript': transcript
                    }))

        except Exception as e:
            print(f"❌ ERROR in speech moderation: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Error processing speech'
                }))
            except Exception:
                pass
    
    @database_sync_to_async
    def get_violation_count(self, user_id, stream_id):
        """Get the number of violations for user in this stream"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = None
            try:
                user_obj = User.objects.filter(pk=user_id).first()
            except Exception:
                user_obj = None

            # Resolve stream object
            stream_obj = None
            try:
                stream_obj = Stream.objects.filter(pk=stream_id).first()
            except Exception:
                stream_obj = None

            if user_obj and stream_obj:
                count = SpeechViolation.objects.filter(user=user_obj, stream=stream_obj).count()
            elif user_obj and not stream_obj:
                count = SpeechViolation.objects.filter(user=user_obj, stream_identifier=str(stream_id)).count()
            elif not user_obj and stream_obj:
                count = SpeechViolation.objects.filter(user_identifier=str(user_id), stream=stream_obj).count()
            else:
                count = SpeechViolation.objects.filter(user_identifier=str(user_id), stream_identifier=str(stream_id)).count()

            print(f"📊 Current violation count for user {user_id} in stream {stream_id}: {count}")
            return count
        except Exception as e:
            print(f"❌ Error getting violation count for {user_id}: {e}")
            return 0
    
    @database_sync_to_async
    def log_violation(self, user_id, stream_id, transcript, toxicity_score, detected_words, violation_count):
        """Log a speech violation"""
        violation_type = 'warning'
        if violation_count == 2:
            violation_type = 'timeout'
        elif violation_count >= 3:
            violation_type = 'stream_stop'

        # Try to resolve an actual User record; otherwise store user_identifier
        user_obj = None
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_obj = User.objects.filter(pk=user_id).first()
            except Exception:
                user_obj = None
        except Exception:
            user_obj = None

        # Try to resolve Stream as well
        stream_obj = None
        try:
            try:
                stream_obj = Stream.objects.filter(pk=stream_id).first()
            except Exception:
                stream_obj = None
        except Exception:
            stream_obj = None

        if user_obj:
            if stream_obj:
                violation = SpeechViolation.objects.create(
                    user=user_obj,
                    stream=stream_obj,
                    transcript=transcript,
                    toxicity_score=toxicity_score,
                    detected_words=detected_words,
                    violation_type=violation_type
                )
            else:
                violation = SpeechViolation.objects.create(
                    user=user_obj,
                    stream=None,
                    stream_identifier=str(stream_id),
                    transcript=transcript,
                    toxicity_score=toxicity_score,
                    detected_words=detected_words,
                    violation_type=violation_type
                )
        else:
            if stream_obj:
                violation = SpeechViolation.objects.create(
                    user=None,
                    user_identifier=str(user_id),
                    stream=stream_obj,
                    transcript=transcript,
                    toxicity_score=toxicity_score,
                    detected_words=detected_words,
                    violation_type=violation_type
                )
            else:
                violation = SpeechViolation.objects.create(
                    user=None,
                    user_identifier=str(user_id),
                    stream=None,
                    stream_identifier=str(stream_id),
                    transcript=transcript,
                    toxicity_score=toxicity_score,
                    detected_words=detected_words,
                    violation_type=violation_type
                )

        print(f"💾 Logged violation #{violation_count} (ID: {violation.id}, Type: {violation_type})")
        return violation
    
    @database_sync_to_async
    def issue_timeout(self, user_id, stream_id, duration_seconds):
        """Issue a timeout for the user"""
        expires_at = timezone.now() + timedelta(seconds=duration_seconds)
        # Try to resolve User and Stream, otherwise use identifiers
        user_obj = None
        stream_obj = None
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_obj = User.objects.filter(pk=user_id).first()
            except Exception:
                user_obj = None
        except Exception:
            user_obj = None

        try:
            try:
                stream_obj = Stream.objects.filter(pk=stream_id).first()
            except Exception:
                stream_obj = None
        except Exception:
            stream_obj = None

        if user_obj and stream_obj:
            timeout = StreamTimeout.objects.create(
                user=user_obj,
                stream=stream_obj,
                duration_seconds=duration_seconds,
                reason="Automatic: Speech violation timeout",
                expires_at=expires_at,
                is_active=True
            )
        elif user_obj and not stream_obj:
            timeout = StreamTimeout.objects.create(
                user=user_obj,
                stream=None,
                stream_identifier=str(stream_id),
                duration_seconds=duration_seconds,
                reason="Automatic: Speech violation timeout",
                expires_at=expires_at,
                is_active=True
            )
        elif not user_obj and stream_obj:
            timeout = StreamTimeout.objects.create(
                user=None,
                user_identifier=str(user_id),
                stream=stream_obj,
                duration_seconds=duration_seconds,
                reason="Automatic: Speech violation timeout",
                expires_at=expires_at,
                is_active=True
            )
        else:
            timeout = StreamTimeout.objects.create(
                user=None,
                user_identifier=str(user_id),
                stream=None,
                stream_identifier=str(stream_id),
                duration_seconds=duration_seconds,
                reason="Automatic: Speech violation timeout",
                expires_at=expires_at,
                is_active=True
            )
        print(f"⏰ Timeout issued: {duration_seconds}s (expires at {expires_at})")
        return timeout

    @database_sync_to_async
    def deactivate_expired_timeouts(self, user_id, stream_id):
        """Mark any expired timeouts for this user+stream as inactive."""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = None
            try:
                user_obj = User.objects.filter(pk=user_id).first()
            except Exception:
                user_obj = None

            # Resolve stream object
            stream_obj = None
            try:
                stream_obj = Stream.objects.filter(pk=stream_id).first()
            except Exception:
                stream_obj = None

            if user_obj and stream_obj:
                StreamTimeout.objects.filter(user=user_obj, stream=stream_obj, is_active=True, expires_at__lte=timezone.now()).update(is_active=False)
            elif user_obj and not stream_obj:
                StreamTimeout.objects.filter(user=user_obj, stream_identifier=str(stream_id), is_active=True, expires_at__lte=timezone.now()).update(is_active=False)
            elif not user_obj and stream_obj:
                StreamTimeout.objects.filter(user_identifier=str(user_id), stream=stream_obj, is_active=True, expires_at__lte=timezone.now()).update(is_active=False)
            else:
                StreamTimeout.objects.filter(user_identifier=str(user_id), stream_identifier=str(stream_id), is_active=True, expires_at__lte=timezone.now()).update(is_active=False)
        except Exception as e:
            print(f"❌ Error deactivating expired timeouts for {user_id}/{stream_id}: {e}")
    
    @database_sync_to_async
    def check_timeout(self, user_id, stream_id):
        """Check if user is currently timed out"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = None
            try:
                user_obj = User.objects.filter(pk=user_id).first()
            except Exception:
                user_obj = None

            # Resolve stream object if available
            stream_obj = None
            try:
                stream_obj = Stream.objects.filter(pk=stream_id).first()
            except Exception:
                stream_obj = None

            if user_obj and stream_obj:
                active_timeout = StreamTimeout.objects.filter(
                    user=user_obj,
                    stream=stream_obj,
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).exists()
            elif user_obj and not stream_obj:
                active_timeout = StreamTimeout.objects.filter(
                    user=user_obj,
                    stream_identifier=str(stream_id),
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).exists()
            elif not user_obj and stream_obj:
                active_timeout = StreamTimeout.objects.filter(
                    user_identifier=str(user_id),
                    stream=stream_obj,
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).exists()
            else:
                active_timeout = StreamTimeout.objects.filter(
                    user_identifier=str(user_id),
                    stream_identifier=str(stream_id),
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).exists()
        except Exception as e:
            print(f"❌ Error checking timeout for {user_id}: {e}")
            active_timeout = False

        if active_timeout:
            print(f"⏸️  User {user_id} is currently timed out")

        return active_timeout
    
    async def _schedule_timeout_expiry(self, user_id, stream_id, duration_seconds):
        """Background task to wait for timeout expiry, deactivate it and notify the group."""
        try:
            await asyncio.sleep(duration_seconds)
            # Deactivate expired timeouts in DB
            try:
                await self.deactivate_expired_timeouts(user_id, stream_id)
            except Exception as e:
                print(f"❌ Error deactivating timeout in DB: {e}")

            # Notify the group that timeout expired for this user
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'timeout_expired_notification',
                        'user_id': str(user_id),
                        'stream_id': str(stream_id),
                    }
                )
            except Exception as e:
                print(f"❌ Error sending timeout_expired notification: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Error in timeout expiry scheduler: {e}")

    async def timeout_expired_notification(self, event):
        """Group handler: notify clients about timeout expiry for a user."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'timeout_expired',
                'user_id': event.get('user_id'),
                'stream_id': event.get('stream_id'),
                'message': 'Your timeout has expired'
            }))
        except Exception as e:
            print(f"❌ Failed to send timeout_expired to client: {e}")
    @database_sync_to_async
    def stop_stream(self, stream_id):
        """Stop the stream"""
        try:
            stream = Stream.objects.get(id=stream_id)
            stream.status = 'ended'
            stream.ended_at = timezone.now()
            stream.save()
            print(f"🛑 Stream {stream_id} has been stopped")
        except Stream.DoesNotExist:
            print(f"❌ Stream {stream_id} not found")
            pass