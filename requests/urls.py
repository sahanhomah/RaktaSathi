from django.urls import path

from . import views

app_name = 'requests'

urlpatterns = [
    path('', views.home, name='home'),
    path('request/', views.request_blood, name='request'),
    path('track/', views.track_request, name='track_request'),
]
