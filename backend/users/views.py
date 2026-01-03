from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model

User = get_user_model()
from .serializers import UserSerializer, RegisterSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            login(request, user)
            return Response({
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            })
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'})

class CurrentUserView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        return Response(
            {'error': 'Not authenticated'},
            status=status.HTTP_401_UNAUTHORIZED
        )
