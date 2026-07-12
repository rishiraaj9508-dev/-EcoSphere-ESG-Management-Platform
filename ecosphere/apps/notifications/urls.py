from django.urls import path
from .views import NotificationSettingsView, NotificationListView, NotificationMarkReadView

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('settings/', NotificationSettingsView.as_view(), name='settings'),
    path('<int:pk>/read/', NotificationMarkReadView.as_view(), name='read'),
]
