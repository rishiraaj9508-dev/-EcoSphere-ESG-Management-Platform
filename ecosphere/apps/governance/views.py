from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
import json

from apps.accounts.mixins import RoleRequiredMixin
from .models import ESGPolicy, PolicyAcknowledgement, Audit, ComplianceIssue
from apps.notifications.services import NotificationService

# 1. ESG Policies
class ESGPolicyListView(LoginRequiredMixin, ListView):
    model = ESGPolicy
    template_name = 'governance/policy_list.html'
    context_object_name = 'policies'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['acknowledged_ids'] = PolicyAcknowledgement.objects.filter(employee=user).values_list('policy_id', flat=True)
        return context

class ESGPolicyCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = ESGPolicy
    fields = ['title', 'description', 'category', 'version', 'effective_date', 'review_cycle', 'status']
    template_name = 'governance/policy_form.html'
    success_url = reverse_lazy('governance:policies')
    allowed_roles = ['super_admin', 'esg_manager']

class ESGPolicyPublishView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager']

    def post(self, request, pk):
        policy = get_object_or_404(ESGPolicy, pk=pk)
        policy.status = 'active'
        policy.save()

        # If has parent policy, supersede it and clear acknowledgements
        if policy.parent_policy:
            parent = policy.parent_policy
            parent.status = 'superseded'
            parent.save()
            PolicyAcknowledgement.objects.filter(policy=parent).delete()

        # Send in-app notification to all employees
        employees = User.objects.filter(profile__role='employee')
        NotificationService.send(
            recipients=employees,
            event_type='POLICY_PUBLISHED',
            title=f"Policy Published: {policy.title}",
            message=f"A new ESG Policy '{policy.title}' (v{policy.version}) has been published. Please review and acknowledge it."
        )

        messages.success(request, f"Policy v{policy.version} published successfully!")
        return redirect('governance:policies')

class ESGPolicyNewVersionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager']

    def post(self, request, pk):
        old_policy = get_object_or_404(ESGPolicy, pk=pk)
        try:
            v_float = float(old_policy.version)
            new_version = f"{v_float + 1.0:.1f}"
        except ValueError:
            new_version = old_policy.version + ".1"

        new_policy = ESGPolicy.objects.create(
            title=old_policy.title,
            description=old_policy.description,
            category=old_policy.category,
            version=new_version,
            effective_date=timezone.now().date(),
            review_cycle=old_policy.review_cycle,
            status='draft',
            parent_policy=old_policy
        )

        messages.success(request, f"Draft for new version (v{new_policy.version}) created.")
        return redirect('governance:policies')

class PolicyAcknowledgeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        policy = get_object_or_404(ESGPolicy, pk=pk, status='active')
        ack, created = PolicyAcknowledgement.objects.get_or_create(
            policy=policy,
            employee=request.user
        )
        if created:
            messages.success(request, f"Successfully acknowledged policy: {policy.title}!")
        else:
            messages.info(request, "You have already acknowledged this policy.")
        return redirect('governance:policies')


# 2. Audits
class AuditListView(LoginRequiredMixin, ListView):
    model = Audit
    template_name = 'governance/audit_list.html'
    context_object_name = 'audits'

class AuditCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Audit
    fields = ['title', 'department', 'scope', 'auditor', 'audit_date', 'findings', 'resolution_notes', 'status']
    template_name = 'governance/audit_form.html'
    success_url = reverse_lazy('governance:audits')
    allowed_roles = ['super_admin', 'esg_manager']

class AuditUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Audit
    fields = ['title', 'department', 'scope', 'auditor', 'audit_date', 'findings', 'resolution_notes', 'status']
    template_name = 'governance/audit_form.html'
    success_url = reverse_lazy('governance:audits')
    allowed_roles = ['super_admin', 'esg_manager']


# 3. Compliance Issues
class ComplianceIssueListView(LoginRequiredMixin, ListView):
    model = ComplianceIssue
    template_name = 'governance/issue_list.html'
    context_object_name = 'issues'

    def get_queryset(self):
        qs = super().get_queryset().select_related('department', 'owner')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == 'dept_head' and profile.department:
            qs = qs.filter(department=profile.department)
        elif profile and profile.role == 'employee':
            qs = qs.filter(owner=user)
        return qs

class ComplianceIssueCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = ComplianceIssue
    fields = ['title', 'description', 'department', 'owner', 'due_date', 'severity', 'status']
    template_name = 'governance/issue_form.html'
    success_url = reverse_lazy('governance:issues')
    allowed_roles = ['super_admin', 'esg_manager']

    def form_valid(self, form):
        response = super().form_valid(form)
        # Send Notification to owner
        NotificationService.send(
            recipients=self.object.owner,
            event_type='COMPLIANCE_ASSIGNED',
            title=f"New Compliance Issue Assigned: {self.object.title}",
            message=f"You have been assigned a compliance issue: '{self.object.title}'. Due date: {self.object.due_date}."
        )
        return response

class ComplianceIssueUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = ComplianceIssue
    fields = ['title', 'description', 'department', 'owner', 'due_date', 'severity', 'status']
    template_name = 'governance/issue_form.html'
    success_url = reverse_lazy('governance:issues')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

class ComplianceIssueResolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        issue = get_object_or_404(ComplianceIssue, pk=pk)
        
        # Security: owner, manager, admin
        user = request.user
        profile = getattr(user, 'profile', None)
        if issue.owner != user and profile.role not in ['super_admin', 'esg_manager']:
            messages.error(request, "You are not authorized to resolve this compliance issue.")
            return redirect('governance:issues')

        issue.status = 'resolved'
        issue.resolved_at = timezone.now()
        issue.save()
        messages.success(request, f"Compliance issue '{issue.title}' resolved!")
        return redirect('governance:issues')


# 4. Governance Dashboard
class GovernanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/governance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)

        is_scoped = False
        scoped_dept = None
        if profile and profile.role in ['dept_head', 'employee'] and profile.department:
            is_scoped = True
            scoped_dept = profile.department

        audits_qs = Audit.objects.all()
        issues_qs = ComplianceIssue.objects.all()

        if is_scoped:
            audits_qs = audits_qs.filter(department=scoped_dept)
            issues_qs = issues_qs.filter(department=scoped_dept)
            context['dept_name'] = scoped_dept.name
        else:
            context['dept_name'] = "Organization-wide"

        context['is_scoped'] = is_scoped

        # Counts
        context['total_audits'] = audits_qs.count()
        context['open_issues'] = issues_qs.filter(status='open').count()
        context['overdue_issues'] = issues_qs.filter(is_overdue=True).count()

        # Chart 1: Audit completion ratio (planned, in_progress, completed)
        status_counts = audits_qs.values('status').annotate(count=models.Count('status'))
        status_map = {'planned': 0, 'in_progress': 0, 'completed': 0}
        for sc in status_counts:
            if sc['status'] in status_map:
                status_map[sc['status']] = sc['count']

        context['audit_chart_data'] = json.dumps({
            'labels': ['Planned', 'In Progress', 'Completed'],
            'data': [status_map['planned'], status_map['in_progress'], status_map['completed']]
        }, cls=DjangoJSONEncoder)

        # Chart 2: Policy acknowledgement rates
        active_policies = ESGPolicy.objects.filter(status='active')
        policy_labels = []
        policy_rates = []

        total_employees = User.objects.filter(profile__role='employee')
        if is_scoped:
            total_employees = total_employees.filter(profile__department=scoped_dept)
        emp_count = total_employees.count()

        for policy in active_policies:
            policy_labels.append(f"{policy.title} (v{policy.version})")
            acks = PolicyAcknowledgement.objects.filter(policy=policy)
            if is_scoped:
                acks = acks.filter(employee__in=total_employees)
            ack_count = acks.count()
            rate = (ack_count / emp_count * 100) if emp_count > 0 else 0
            policy_rates.append(round(rate, 1))

        context['policy_chart_data'] = json.dumps({
            'labels': policy_labels,
            'rates': policy_rates
        }, cls=DjangoJSONEncoder)

        return context
