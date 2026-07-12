from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
import json

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

# 2. Diversity Metrics
class DiversityMetricListView(LoginRequiredMixin, ListView):
    model = DiversityMetric
    template_name = 'social/diversity_list.html'
    context_object_name = 'metrics'

    def get_queryset(self):
        qs = super().get_queryset().select_related('department')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role in ['employee', 'dept_head'] and profile.department:
            qs = qs.filter(department=profile.department)
        return qs

class DiversityMetricCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = DiversityMetric
    fields = ['department', 'metric_type', 'value', 'unit', 'reporting_period']
    template_name = 'social/diversity_form.html'
    success_url = reverse_lazy('social:diversity')
    allowed_roles = ['super_admin', 'esg_manager']


# 3. Trainings
class TrainingListView(LoginRequiredMixin, ListView):
    model = Training
    template_name = 'social/training_list.html'
    context_object_name = 'trainings'

    def get_queryset(self):
        qs = super().get_queryset().select_related('department')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role in ['employee', 'dept_head'] and profile.department:
            qs = qs.filter(department=profile.department)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)

        completions = TrainingCompletion.objects.select_related('training', 'employee')
        if profile and profile.role == 'dept_head' and profile.department:
            completions = completions.filter(training__department=profile.department)
        elif profile and profile.role == 'employee':
            completions = completions.filter(employee=user)

        context['completions'] = completions
        return context

class TrainingCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Training
    fields = ['title', 'department', 'training_date']
    template_name = 'social/training_form.html'
    success_url = reverse_lazy('social:training')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-create completion stubs for all employees in this department
        dept = self.object.department
        employees = User.objects.filter(profile__department=dept, profile__role='employee')
        for emp in employees:
            TrainingCompletion.objects.get_or_create(
                training=self.object,
                employee=emp
            )
        return response

class TrainingCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        completion = get_object_or_404(TrainingCompletion, pk=pk)
        
        user = request.user
        profile = getattr(user, 'profile', None)
        if completion.employee != user and profile.role not in ['super_admin', 'esg_manager', 'dept_head']:
            messages.error(request, "Not authorized to update this completion.")
            return redirect('social:training')

        completion.completed = True
        completion.save()
        messages.success(request, f"Marked training '{completion.training.title}' as completed!")
        return redirect('social:training')


# 4. Social Dashboard
class SocialDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/social.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)

        is_scoped = False
        scoped_dept = None
        if profile and profile.role in ['dept_head', 'employee'] and profile.department:
            is_scoped = True
            scoped_dept = profile.department

        # Base Querysets
        csr_qs = CSRParticipation.objects.all()
        training_qs = TrainingCompletion.objects.all()
        diversity_qs = DiversityMetric.objects.all()

        if is_scoped:
            csr_qs = csr_qs.filter(activity__department=scoped_dept)
            training_qs = training_qs.filter(training__department=scoped_dept)
            diversity_qs = diversity_qs.filter(department=scoped_dept)
            context['dept_name'] = scoped_dept.name
        else:
            context['dept_name'] = "Organization-wide"

        context['is_scoped'] = is_scoped

        # Metric Counts
        context['total_csr_participations'] = csr_qs.filter(status='approved').count()
        context['total_trainings_scheduled'] = Training.objects.filter(department=scoped_dept).count() if is_scoped else Training.objects.count()

        # 1. CSR Activity Rates
        approved_csr = csr_qs.filter(status='approved').count()
        total_csr = csr_qs.count()
        csr_rate = (approved_csr / total_csr * 100) if total_csr > 0 else 0
        context['csr_rate'] = round(csr_rate, 1)

        # 2. Training Completion Rates
        completed_trainings = training_qs.filter(completed=True).count()
        total_trainings = training_qs.count()
        training_rate = (completed_trainings / total_trainings * 100) if total_trainings > 0 else 0
        context['training_rate'] = round(training_rate, 1)

        # 3. Chart 1: Training Completion Rate vs Pending
        context['training_chart_data'] = json.dumps({
            'labels': ['Completed', 'Pending'],
            'data': [completed_trainings, max(0, total_trainings - completed_trainings)]
        }, cls=DjangoJSONEncoder)

        # 4. Chart 2: Demographics Diversity Metrics
        diversity_labels = []
        diversity_values = []
        # Fetch the latest metric for each metric_type
        metric_types = diversity_qs.values_list('metric_type', flat=True).distinct()
        for mt in metric_types:
            latest_metric = diversity_qs.filter(metric_type=mt).order_by('-reporting_period')
            latest = latest_metric.first()
            if latest:
                diversity_labels.append(f"{latest.metric_type} ({latest.unit})")
                diversity_values.append(float(latest.value))

        context['diversity_chart_data'] = json.dumps({
            'labels': diversity_labels,
            'values': diversity_values
        }, cls=DjangoJSONEncoder)

        return context
