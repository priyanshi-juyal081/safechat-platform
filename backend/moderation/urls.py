from django.urls import path
from . import views

urlpatterns = [
    path('check/', views.ToxicityCheckView.as_view(), name='toxicity-check'),
    path('warnings/', views.WarningListView.as_view(), name='warning-list'),
    path('warnings/user/<int:user_id>/', views.UserWarningsView.as_view(), name='user-warnings'),
    path('restrict/', views.RestrictUserView.as_view(), name='restrict-user'),
    path('restrictions/', views.RestrictionListView.as_view(), name='restriction-list'),
]
