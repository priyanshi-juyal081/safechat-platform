from django.urls import path
from . import views

urlpatterns = [
    path('messages/', views.MessageListView.as_view(), name='message-list'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('streams/', views.StreamListView.as_view(), name='stream-list'),
    path('streams/<int:pk>/', views.StreamDetailView.as_view(), name='stream-detail'),
    path('streams/start/', views.StartStreamView.as_view(), name='start-stream'),
    path('streams/<int:pk>/end/', views.EndStreamView.as_view(), name='end-stream'),
]