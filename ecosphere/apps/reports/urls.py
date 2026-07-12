from django.urls import path
from .views import (
    EnvironmentalReportView, SocialReportView, GovernanceReportView,
    SummaryReportView, CustomReportBuilderView
)

app_name = 'reports'

urlpatterns = [
    path('environmental/', EnvironmentalReportView.as_view(), name='environmental'),
    path('social/', SocialReportView.as_view(), name='social'),
    path('governance/', GovernanceReportView.as_view(), name='governance'),
    path('summary/', SummaryReportView.as_view(), name='summary'),
    path('custom/', CustomReportBuilderView.as_view(), name='custom'),
]
