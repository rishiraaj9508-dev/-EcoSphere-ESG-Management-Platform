from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Avg
import json

from apps.dashboard.models import DepartmentESGScore
from apps.core.models import Department
from apps.governance.models import ComplianceIssue
from apps.gamification.models import Challenge
from apps.social.models import CSRActivity

class MainDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        
        # Determine department scoping
        is_scoped = False
        scoped_dept = None
        if profile and profile.role in ['dept_head', 'employee'] and profile.department:
            is_scoped = True
            scoped_dept = profile.department

        # 1. Fetch scores for KPI cards
        if is_scoped:
            score_record = DepartmentESGScore.objects.filter(department=scoped_dept).first()
            env_score = score_record.environmental_score if score_record else 50.00
            soc_score = score_record.social_score if score_record else 50.00
            gov_score = score_record.governance_score if score_record else 50.00
            overall_score = score_record.overall_score if score_record else 50.00
            dept_name = scoped_dept.name
        else:
            # Org-wide average scores
            avg_scores = DepartmentESGScore.objects.aggregate(
                avg_env=Avg('environmental_score'),
                avg_soc=Avg('social_score'),
                avg_gov=Avg('governance_score'),
                avg_overall=Avg('overall_score')
            )
            env_score = avg_scores['avg_env'] or 50.00
            soc_score = avg_scores['avg_soc'] or 50.00
            gov_score = avg_scores['avg_gov'] or 50.00
            overall_score = avg_scores['avg_overall'] or 50.00
            dept_name = "Organization-wide"

        context['kpi_cards'] = [
            {'label': 'Environmental Score', 'value': round(env_score, 1), 'trend_text': 'Goal progress', 'trend_type': 'up', 'trend_class': 'text-green-400'},
            {'label': 'Social Score', 'value': round(soc_score, 1), 'trend_text': 'CSR & training', 'trend_type': 'up', 'trend_class': 'text-green-400'},
            {'label': 'Governance Score', 'value': round(gov_score, 1), 'trend_text': 'Audits & compliance', 'trend_type': 'up', 'trend_class': 'text-green-400'},
            {'label': 'Overall ESG Score', 'value': round(overall_score, 1), 'trend_text': 'Weighted summary', 'trend_type': 'up', 'trend_class': 'text-green-400'},
        ]
        context['dept_name'] = dept_name
        context['is_scoped'] = is_scoped

        # 2. Leaderboard (Ranked list of departments by ESG score)
        leaderboard = DepartmentESGScore.objects.select_related('department').order_by('-overall_score')
        context['leaderboard'] = leaderboard

        # 3. Counts for Summary widgets
        issue_qs = ComplianceIssue.objects.filter(status='open')
        challenge_qs = Challenge.objects.filter(status='active')
        csr_qs = CSRActivity.objects.filter(status='upcoming')

        if is_scoped:
            issue_qs = issue_qs.filter(department=scoped_dept)
            challenge_qs = challenge_qs.filter(models.Q(target_all=True) | models.Q(departments=scoped_dept))
            csr_qs = csr_qs.filter(department=scoped_dept)

        context['open_issues_count'] = issue_qs.count()
        context['active_challenges_count'] = challenge_qs.count()
        context['upcoming_csr_count'] = csr_qs.count()

        # 4. Chart 1: Grouped bar chart data (Environmental, Social, Governance, Overall Score) per department
        chart_depts = []
        chart_env = []
        chart_soc = []
        chart_gov = []
        chart_overall = []

        all_scores = DepartmentESGScore.objects.select_related('department').all()
        for s in all_scores:
            chart_depts.append(s.department.name)
            chart_env.append(float(s.environmental_score))
            chart_soc.append(float(s.social_score))
            chart_gov.append(float(s.governance_score))
            chart_overall.append(float(s.overall_score))

        context['bar_chart_data'] = json.dumps({
            'labels': chart_depts,
            'env': chart_env,
            'soc': chart_soc,
            'gov': chart_gov,
            'overall': chart_overall
        }, cls=DjangoJSONEncoder)

        # 5. Chart 2: Doughnut chart (ESG component proportions for the overall org or scoped dept)
        context['doughnut_chart_data'] = json.dumps({
            'labels': ['Environmental', 'Social', 'Governance'],
            'scores': [float(env_score), float(soc_score), float(gov_score)]
        }, cls=DjangoJSONEncoder)

        return context
