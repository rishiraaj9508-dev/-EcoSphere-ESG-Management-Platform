from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db import models

from apps.accounts.mixins import RoleRequiredMixin
from apps.social.models import CSRActivity, CSRParticipation, Training, TrainingCompletion, DiversityMetric
from apps.gamification.services import GamificationService

# 1. CSR Activity Views
class CSRActivityListView(LoginRequiredMixin, ListView):
    model = CSRActivity
    template_name = 'social/csr_list.html'
    context_object_name = 'activities'

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'department')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        # Limit to user's department for employees/dept_heads
        if profile and profile.role in ['employee', 'dept_head'] and profile.department:
            qs = qs.filter(department=profile.department)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        
        # Fetch participation queue for approvals (only managers/dept heads see this)
        if profile and profile.role in ['super_admin', 'esg_manager', 'dept_head']:
            queue = CSRParticipation.objects.filter(status='pending_review').select_related('activity', 'employee')
            if profile.role == 'dept_head' and profile.department:
                queue = queue.filter(activity__department=profile.department)
            context['approval_queue'] = queue
        
        # User's own enrolled/participating activities
        context['my_participations'] = CSRParticipation.objects.filter(employee=user).select_related('activity')
        return context


class CSRActivityCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = CSRActivity
    fields = ['title', 'description', 'category', 'department', 'start_date', 'end_date', 'max_participants', 'requires_evidence', 'xp_reward', 'status']
    template_name = 'social/csr_form.html'
    success_url = reverse_lazy('social:csr')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == 'dept_head' and profile.department:
            form.fields['department'].queryset = form.fields['department'].queryset.filter(pk=profile.department.pk)
            form.fields['department'].initial = profile.department
        return form


class CSRActivityUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = CSRActivity
    fields = ['title', 'description', 'category', 'department', 'start_date', 'end_date', 'max_participants', 'requires_evidence', 'xp_reward', 'status']
    template_name = 'social/csr_form.html'
    success_url = reverse_lazy('social:csr')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']


# Enrolment and Evidence submission
class CSRActivityEnrolView(LoginRequiredMixin, View):
    def post(self, request, pk):
        activity = get_object_or_404(CSRActivity, pk=pk)
        
        # Check active status
        if activity.status != 'active':
            messages.error(request, "You can only enrol in active CSR activities.")
            return redirect('social:csr')

        # Check department scope
        profile = getattr(request.user, 'profile', None)
        if profile and profile.department != activity.department and profile.role not in ['super_admin', 'esg_manager']:
            messages.error(request, "This CSR activity is not available for your department.")
            return redirect('social:csr')

        # Check capacity
        current_participants = CSRParticipation.objects.filter(activity=activity).count()
        if current_participants >= activity.max_participants:
            messages.error(request, "This activity is full. Maximum participant limit reached.")
            return redirect('social:csr')

        # Create participation record
        participation, created = CSRParticipation.objects.get_or_create(
            activity=activity,
            employee=request.user,
            defaults={'status': 'enrolled'}
        )
        if created:
            messages.success(request, f"Successfully enrolled in {activity.title}!")
        else:
            messages.info(request, "You are already enrolled in this activity.")
            
        return redirect('social:csr')


class CSRParticipationSubmitView(LoginRequiredMixin, View):
    def post(self, request, pk):
        participation = get_object_or_404(CSRParticipation, pk=pk, employee=request.user)
        
        if participation.status != 'enrolled':
            messages.error(request, "You can only submit evidence for enrolled activities.")
            return redirect('social:csr')

        evidence_url = request.POST.get('evidence_url', '').strip()
        evidence_file = request.FILES.get('evidence_file')

        if participation.activity.requires_evidence and not (evidence_url or evidence_file):
            messages.error(request, "This activity requires you to upload a file or submit an evidence URL.")
            return redirect('social:csr')

        participation.status = 'pending_review'
        if evidence_url:
            participation.evidence_url = evidence_url
        if evidence_file:
            participation.evidence_file = evidence_file
        participation.submitted_at = timezone.now()
        participation.save()

        messages.success(request, "Evidence submitted successfully. Pending review.")
        return redirect('social:csr')


class CSRParticipationApproveView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def post(self, request, pk):
        participation = get_object_or_404(CSRParticipation, pk=pk)
        
        if participation.status != 'pending_review':
            messages.error(request, "Participation is not pending review.")
            return redirect('social:csr')

        participation.status = 'approved'
        participation.reviewed_at = timezone.now()
        participation.reviewed_by = request.user
        participation.save()

        # Award XP via GamificationService
        if participation.activity.xp_reward > 0:
            GamificationService.award_xp(
                employee=participation.employee,
                amount=participation.activity.xp_reward,
                source='csr',
                reference_id=participation.pk,
                note=f"Approved CSR activity: {participation.activity.title}"
            )
            messages.success(request, f"Participation approved! Configured {participation.activity.xp_reward} XP awarded.")
        else:
            messages.success(request, "Participation approved.")

        return redirect('social:csr')


class CSRParticipationRejectView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def post(self, request, pk):
        participation = get_object_or_404(CSRParticipation, pk=pk)
        
        if participation.status != 'pending_review':
            messages.error(request, "Participation is not pending review.")
            return redirect('social:csr')

        participation.status = 'rejected'
        participation.reviewed_at = timezone.now()
        participation.reviewed_by = request.user
        participation.save()

        messages.success(request, "Participation rejected.")
        return redirect('social:csr')

class DiversityMetricListView(LoginRequiredMixin, ListView):
    model = DiversityMetric
    template_name = 'social/diversity_list.html'
    context_object_name = 'metrics'

class TrainingListView(LoginRequiredMixin, ListView):
    model = Training
    template_name = 'social/training_list.html'
    context_object_name = 'trainings'
