from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class NotificationSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/settings.html'
