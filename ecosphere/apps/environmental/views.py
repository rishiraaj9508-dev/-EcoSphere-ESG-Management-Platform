from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Sum, Avg
from django.core.serializers.json import DjangoJSONEncoder
import json
import datetime

from apps.accounts.mixins import RoleRequiredMixin
from apps.environmental.models import EmissionFactor, CarbonEmission, SustainabilityGoal
from apps.core.models import Department

# 1. Emission Factors
class EmissionFactorListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = EmissionFactor
    template_name = 'environmental/emission_factor_list.html'
    context_object_name = 'factors'
    allowed_roles = ['super_admin', 'esg_manager']

class EmissionFactorCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = EmissionFactor
    fields = ['name', 'unit', 'coefficient', 'is_active']
    template_name = 'environmental/emission_factor_form.html'
    success_url = reverse_lazy('environmental:emissions')
    allowed_roles = ['super_admin', 'esg_manager']

class EmissionFactorUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = EmissionFactor
    fields = ['name', 'unit', 'coefficient', 'is_active']
    template_name = 'environmental/emission_factor_form.html'
    success_url = reverse_lazy('environmental:emissions')
    allowed_roles = ['super_admin', 'esg_manager']


# 2. Carbon Emissions
class CarbonEmissionListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = CarbonEmission
    template_name = 'environmental/emission_list.html'
    context_object_name = 'emissions'
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def get_queryset(self):
        qs = super().get_queryset().select_related('department', 'emission_factor')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == 'dept_head' and profile.department:
            qs = qs.filter(department=profile.department)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Also pass active factors for Settings/Config tab
        context['factors'] = EmissionFactor.objects.all()
        return context

class CarbonEmissionCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = CarbonEmission
    fields = ['department', 'emission_source', 'activity_value', 'emission_factor', 'auto_recalculate', 'reporting_period']
    template_name = 'environmental/emission_form.html'
    success_url = reverse_lazy('environmental:emissions')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == 'dept_head' and profile.department:
            form.fields['department'].queryset = Department.objects.filter(pk=profile.department.pk)
            form.fields['department'].initial = profile.department
        return form

class CarbonEmissionUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = CarbonEmission
    fields = ['department', 'emission_source', 'activity_value', 'emission_factor', 'auto_recalculate', 'reporting_period']
    template_name = 'environmental/emission_form.html'
    success_url = reverse_lazy('environmental:emissions')
    allowed_roles = ['super_admin', 'esg_manager', 'dept_head']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == 'dept_head' and profile.department:
            form.fields['department'].queryset = Department.objects.filter(pk=profile.department.pk)
        return form


# 3. Sustainability Goals
class SustainabilityGoalListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = SustainabilityGoal
    template_name = 'environmental/goal_list.html'
    context_object_name = 'goals'
    allowed_roles = ['super_admin', 'esg_manager']

class SustainabilityGoalCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = SustainabilityGoal
    fields = ['title', 'target_metric', 'target_value', 'current_value', 'unit', 'deadline', 'scope', 'department', 'status']
    template_name = 'environmental/goal_form.html'
    success_url = reverse_lazy('environmental:goals')
    allowed_roles = ['super_admin', 'esg_manager']

class SustainabilityGoalUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = SustainabilityGoal
    fields = ['title', 'target_metric', 'target_value', 'current_value', 'unit', 'deadline', 'scope', 'department', 'status']
    template_name = 'environmental/goal_form.html'
    success_url = reverse_lazy('environmental:goals')
    allowed_roles = ['super_admin', 'esg_manager']


# 4. Environmental Dashboard
class EnvironmentalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/environmental.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        
        is_scoped = False
        scoped_dept = None
        if profile and profile.role in ['dept_head', 'employee'] and profile.department:
            is_scoped = True
            scoped_dept = profile.department

        # Filter emissions and goals
        emissions_qs = CarbonEmission.objects.all().select_related('department')
        goals_qs = SustainabilityGoal.objects.all()

        if is_scoped:
            emissions_qs = emissions_qs.filter(department=scoped_dept)
            goals_qs = goals_qs.filter(models.Q(scope='org') | models.Q(department=scoped_dept))
            context['dept_name'] = scoped_dept.name
        else:
            context['dept_name'] = "Organization-wide"

        context['is_scoped'] = is_scoped

        # 1. Total CO2e Emissions
        total_co2e = emissions_qs.aggregate(total=Sum('co2e_value'))['total'] or 0
        context['total_co2e'] = round(total_co2e, 2)

        # 2. Sustainability Goals
        context['goals'] = goals_qs.order_by('deadline')

        # 3. Chart 1: Time-series CO2e Emissions per month (reporting_period)
        # Group by reporting_period
        monthly_emissions = emissions_qs.values('reporting_period').annotate(total_co2e=Sum('co2e_value')).order_by('reporting_period')
        labels = []
        data_co2e = []
        for me in monthly_emissions:
            labels.append(me['reporting_period'].strftime('%b %Y'))
            data_co2e.append(float(me['total_co2e']))

        context['time_series_data'] = json.dumps({
            'labels': labels,
            'data': data_co2e
        }, cls=DjangoJSONEncoder)

        # 4. Chart 2: Department Comparisons (Ranking by emissions)
        dept_ranking = CarbonEmission.objects.values('department__name').annotate(total_co2e=Sum('co2e_value')).order_by('-total_co2e')
        dept_labels = []
        dept_data = []
        for dr in dept_ranking:
            dept_labels.append(dr['department__name'])
            dept_data.append(float(dr['total_co2e']))

        context['dept_comparison_data'] = json.dumps({
            'labels': dept_labels,
            'data': dept_data
        }, cls=DjangoJSONEncoder)

        return context
