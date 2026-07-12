from django.urls import path
from .views import NotificationSettingsView

app_name = 'notifications'

urlpatterns = [
    path('settings/', NotificationSettingsView.as_view(), name='settings'),
]
