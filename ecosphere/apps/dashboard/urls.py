from django.urls import path
from .views import MainDashboardView

app_name = 'dashboard'

urlpatterns = [
    path('', MainDashboardView.as_view(), name='main'),
]
