from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .models import Warning, Restriction
from .serializers import WarningSerializer, RestrictionSerializer
from .ai_detector import ToxicityDetector

class ToxicityCheckView(APIView):
    def post(self, request):
        text = request.data.get('text', '')
        method = request.data.get('method', 'keyword')
        
        detector = ToxicityDetector(method=method)
        result = detector.analyze(text)
        
        return Response(result)

class WarningListView(generics.ListAPIView):
    queryset = Warning.objects.all().select_related('user')
    serializer_class = WarningSerializer

class UserWarningsView(APIView):
    def get(self, request, user_id):
        warnings = Warning.objects.filter(user_id=user_id).order_by('-created_at')
        serializer = WarningSerializer(warnings, many=True)
        return Response({
            'count': warnings.count(),
            'warnings': serializer.data
        })

class RestrictUserView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        restriction_type = request.data.get('restriction_type', 'chat')
        reason = request.data.get('reason', 'Manual restriction')
        is_permanent = request.data.get('is_permanent', False)
        
        try:
            user = User.objects.get(id=user_id)
            
            restriction = Restriction.objects.create(
                user=user,
                restriction_type=restriction_type,
                reason=reason,
                issued_by=request.user if request.user.is_authenticated else None,
                is_permanent=is_permanent
            )
            
            return Response(
                RestrictionSerializer(restriction).data,
                status=status.HTTP_201_CREATED
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class RestrictionListView(generics.ListAPIView):
    queryset = Restriction.objects.all().select_related('user')
    serializer_class = RestrictionSerializer