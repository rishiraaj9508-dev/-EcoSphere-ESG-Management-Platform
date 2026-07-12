from django.urls import path
from .views import NotificationSettingsView, NotificationListView

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('settings/', NotificationSettingsView.as_view(), name='settings'),
]
