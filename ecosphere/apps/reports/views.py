from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class EnvironmentalReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/environmental.html'

class SocialReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/social.html'

class GovernanceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/governance.html'

class SummaryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/summary.html'

class CustomReportBuilderView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/custom.html'
