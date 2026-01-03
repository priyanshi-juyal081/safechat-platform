from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models import Message, Stream
from .serializers import MessageSerializer, StreamSerializer
from moderation.ai_detector import ToxicityDetector

class MessageListView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        queryset = Message.objects.all().select_related('user')
        stream_id = self.request.query_params.get('stream_id', None)
        
        if stream_id:
            queryset = queryset.filter(stream_id=stream_id)
        else:
            queryset = queryset.filter(stream__isnull=True)
        
        return queryset.order_by('-created_at')[:50]
    
    def perform_create(self, serializer):
        # Check toxicity
        detector = ToxicityDetector(method='keyword')
        result = detector.analyze(self.request.data.get('text', ''))
        
        serializer.save(
            user=self.request.user,
            is_flagged=result['is_toxic'],
            toxicity_score=result['toxicity_score']
        )

class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class StreamListView(generics.ListAPIView):
    serializer_class = StreamSerializer
    
    def get_queryset(self):
        return Stream.objects.filter(status='live').select_related('streamer')

class StreamDetailView(generics.RetrieveAPIView):
    queryset = Stream.objects.all()
    serializer_class = StreamSerializer

class StartStreamView(APIView):
    def post(self, request):
        title = request.data.get('title')
        description = request.data.get('description', '')
        
        if not title:
            return Response(
                {'error': 'Title is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stream = Stream.objects.create(
            streamer=request.user,
            title=title,
            description=description,
            status='live'
        )
        
        return Response(
            StreamSerializer(stream).data,
            status=status.HTTP_201_CREATED
        )

class EndStreamView(APIView):
    def post(self, request, pk):
        try:
            stream = Stream.objects.get(pk=pk, streamer=request.user)
            stream.status = 'ended'
            stream.ended_at = timezone.now()
            stream.save()
            
            return Response(StreamSerializer(stream).data)
        except Stream.DoesNotExist:
            return Response(
                {'error': 'Stream not found'},
                status=status.HTTP_404_NOT_FOUND
            )

