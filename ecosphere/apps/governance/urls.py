from django.urls import path
from .views import (
    ESGPolicyListView, ESGPolicyCreateView, ESGPolicyPublishView, ESGPolicyNewVersionView, PolicyAcknowledgeView,
    AuditListView, AuditCreateView, AuditUpdateView,
    ComplianceIssueListView, ComplianceIssueCreateView, ComplianceIssueUpdateView, ComplianceIssueResolveView,
    GovernanceDashboardView
)

app_name = 'governance'

urlpatterns = [
    # Policies
    path('policies/', ESGPolicyListView.as_view(), name='policies'),
    path('policies/add/', ESGPolicyCreateView.as_view(), name='policy-add'),
    path('policies/<int:pk>/publish/', ESGPolicyPublishView.as_view(), name='policy-publish'),
    path('policies/<int:pk>/new-version/', ESGPolicyNewVersionView.as_view(), name='policy-new-version'),
    path('policies/<int:pk>/acknowledge/', PolicyAcknowledgeView.as_view(), name='policy-acknowledge'),

    # Audits
    path('audits/', AuditListView.as_view(), name='audits'),
    path('audits/add/', AuditCreateView.as_view(), name='audit-add'),
    path('audits/<int:pk>/edit/', AuditUpdateView.as_view(), name='audit-edit'),

    # Compliance Issues
    path('issues/', ComplianceIssueListView.as_view(), name='issues'),
    path('issues/add/', ComplianceIssueCreateView.as_view(), name='issue-add'),
    path('issues/<int:pk>/edit/', ComplianceIssueUpdateView.as_view(), name='issue-edit'),
    path('issues/<int:pk>/resolve/', ComplianceIssueResolveView.as_view(), name='issue-resolve'),

    # Dashboard
    path('dashboard/', GovernanceDashboardView.as_view(), name='dashboard'),
]
