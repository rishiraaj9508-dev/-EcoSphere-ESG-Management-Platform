from django.urls import path
from .views import PolicyListView, AuditListView, ComplianceIssueListView

app_name = 'governance'

urlpatterns = [
    path('policies/', PolicyListView.as_view(), name='policies'),
    path('audits/', AuditListView.as_view(), name='audits'),
    path('issues/', ComplianceIssueListView.as_view(), name='issues'),
]
