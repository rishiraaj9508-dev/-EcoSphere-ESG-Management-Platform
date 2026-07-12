from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from datetime import datetime

from apps.accounts.mixins import RoleRequiredMixin
from apps.core.models import Department
from .models import CustomReportAudit
from .services import ReportService

class BaseReportView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager']
    report_type = None  # environmental, social, governance, summary

    def get(self, request):
        departments = Department.objects.filter(is_active=True)
        return render(request, f'reports/{self.report_type}.html', {'departments': departments})

    def post(self, request):
        date_from_str = request.POST.get('date_from', '').strip()
        date_to_str = request.POST.get('date_to', '').strip()
        dept_ids = request.POST.getlist('departments')
        export_format = request.POST.get('format', 'csv').lower()

        # Fallbacks
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date() if date_from_str else timezone.now().date()
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else timezone.now().date()
        except ValueError:
            date_from = timezone.now().date()
            date_to = timezone.now().date()

        depts = Department.objects.filter(id__in=dept_ids) if dept_ids else None

        # Build data based on report type
        if self.report_type == 'environmental':
            data = ReportService.build_environmental(date_from, date_to, depts)
        elif self.report_type == 'social':
            data = ReportService.build_social(date_from, date_to, depts)
        elif self.report_type == 'governance':
            data = ReportService.build_governance(date_from, date_to, depts)
        else:
            data = ReportService.build_esg_summary(date_from, date_to, depts)

        filename = f"{self.report_type}_report_{timezone.now().strftime('%Y%m%d%H%M%S')}"

        if export_format == 'excel':
            return ReportService.export_excel(filename, data)
        elif export_format == 'pdf':
            return ReportService.export_pdf(filename, data["title"], data)
        else:
            return ReportService.export_csv(filename, data)


class EnvironmentalReportView(BaseReportView):
    report_type = 'environmental'

class SocialReportView(BaseReportView):
    report_type = 'social'

class GovernanceReportView(BaseReportView):
    report_type = 'governance'

class SummaryReportView(BaseReportView):
    report_type = 'summary'


class CustomReportBuilderView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager']

    def get(self, request):
        departments = Department.objects.filter(is_active=True)
        return render(request, 'reports/custom.html', {'departments': departments})

    def post(self, request):
        modules = request.POST.getlist('modules')  # environmental, social, governance
        date_from_str = request.POST.get('date_from', '').strip()
        date_to_str = request.POST.get('date_to', '').strip()
        dept_ids = request.POST.getlist('departments')
        export_format = request.POST.get('format', 'csv').lower()

        if not modules:
            messages.error(request, "Please select at least one module category to build your custom report.")
            return redirect('reports:custom')

        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date() if date_from_str else timezone.now().date()
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else timezone.now().date()
        except ValueError:
            date_from = timezone.now().date()
            date_to = timezone.now().date()

        depts = Department.objects.filter(id__in=dept_ids) if dept_ids else Department.objects.all()

        # Log to Audit DB
        audit = CustomReportAudit.objects.create(
            generated_by=request.user,
            modules=modules,
            date_from=date_from,
            date_to=date_to,
            export_format=export_format
        )
        if dept_ids:
            audit.departments.set(depts)

        # Merge Report Data
        merged_title = "Merged Custom ESG Report"
        merged_headers = ["Module", "Date", "Department", "Details / Title", "Value / Target", "Status"]
        merged_rows = []

        if 'environmental' in modules:
            env_data = ReportService.build_environmental(date_from, date_to, depts)
            for r in env_data["rows"]:
                merged_rows.append(["Environmental", r[0], r[1], r[3], r[4], r[5]])

        if 'social' in modules:
            soc_data = ReportService.build_social(date_from, date_to, depts)
            for r in soc_data["rows"]:
                merged_rows.append(["Social", r[0], r[1], r[4], r[5], r[5]])

        if 'governance' in modules:
            gov_data = ReportService.build_governance(date_from, date_to, depts)
            for r in gov_data["rows"]:
                merged_rows.append(["Governance", r[0], r[1], r[4], r[5], r[5]])

        report_data = {
            "title": merged_title,
            "headers": merged_headers,
            "rows": merged_rows
        }

        filename = f"custom_esg_report_{timezone.now().strftime('%Y%m%d%H%M%S')}"

        if export_format == 'excel':
            return ReportService.export_excel(filename, report_data)
        elif export_format == 'pdf':
            return ReportService.export_pdf(filename, merged_title, report_data)
        else:
            return ReportService.export_csv(filename, report_data)
