from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ESGPolicy, Audit, ComplianceIssue

class PolicyListView(LoginRequiredMixin, ListView):
    model = ESGPolicy
    template_name = 'governance/policy_list.html'
    context_object_name = 'policies'

class AuditListView(LoginRequiredMixin, ListView):
    model = Audit
    template_name = 'governance/audit_list.html'
    context_object_name = 'audits'

class ComplianceIssueListView(LoginRequiredMixin, ListView):
    model = ComplianceIssue
    template_name = 'governance/issue_list.html'
    context_object_name = 'issues'
