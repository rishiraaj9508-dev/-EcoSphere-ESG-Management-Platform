from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone

from .models import Notification, NotificationPreference

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        messages.success(request, "Notification marked as read.")
        return redirect('notifications:list')


class NotificationSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        event_types = ['POLICY_PUBLISHED', 'CHALLENGE_STATUS', 'BADGE_UNLOCKED', 'COMPLIANCE_ASSIGNED', 'COMPLIANCE_OVERDUE', 'GOAL_STATUS']
        prefs = []
        for et in event_types:
            pref, _ = NotificationPreference.objects.get_or_create(user=user, event_type=et)
            prefs.append(pref)
        context['preferences'] = prefs
        return context

    def post(self, request):
        user = request.user
        event_types = ['POLICY_PUBLISHED', 'CHALLENGE_STATUS', 'BADGE_UNLOCKED', 'COMPLIANCE_ASSIGNED', 'COMPLIANCE_OVERDUE', 'GOAL_STATUS']
        for et in event_types:
            pref, _ = NotificationPreference.objects.get_or_create(user=user, event_type=et)
            pref.email_enabled = f"email_{et}" in request.POST
            pref.in_app_enabled = f"in_app_{et}" in request.POST
            pref.save()
        messages.success(request, "Preferences saved successfully.")
        return redirect('notifications:settings')
