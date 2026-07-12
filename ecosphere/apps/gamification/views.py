from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.db.models import Sum

from apps.accounts.mixins import RoleRequiredMixin
from apps.gamification.models import Challenge, ChallengeEnrolment, Badge, BadgeAward, Reward, RedemptionTransaction, XPLedger
from apps.core.models import Department
from apps.dashboard.models import DepartmentESGScore
from apps.gamification.services import GamificationService

# 1. Challenges
class ChallengeListView(LoginRequiredMixin, ListView):
    model = Challenge
    template_name = 'gamification/challenge_list.html'
    context_object_name = 'challenges'

    def get_queryset(self):
        qs = super().get_queryset().select_related('category')
        user = self.request.user
        profile = getattr(user, 'profile', None)
        # Limit to active/completed/archived for employees, target scoped departments
        if profile and profile.role == 'employee':
            qs = qs.filter(status__in=['active', 'completed', 'under_review'])
            if profile.department:
                qs = qs.filter(models.Q(target_all=True) | models.Q(departments=profile.department))
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Fetch user's own enrollments
        context['my_enrollments'] = ChallengeEnrolment.objects.filter(employee=user).select_related('challenge')
        return context


class ChallengeCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Challenge
    fields = ['title', 'description', 'category', 'xp_reward', 'start_date', 'end_date', 'target_all', 'departments', 'status']
    template_name = 'gamification/challenge_form.html'
    success_url = reverse_lazy('gamification:challenges')
    allowed_roles = ['super_admin', 'esg_manager']


class ChallengeEnrolView(LoginRequiredMixin, View):
    def post(self, request, pk):
        challenge = get_object_or_404(Challenge, pk=pk)
        
        if challenge.status != 'active':
            messages.error(request, "You can only join active challenges.")
            return redirect('gamification:challenges')

        # Check target audience
        profile = getattr(request.user, 'profile', None)
        if profile and not challenge.target_all and profile.department:
            if not challenge.departments.filter(pk=profile.department.pk).exists() and profile.role not in ['super_admin', 'esg_manager']:
                messages.error(request, "This challenge is not targeted to your department.")
                return redirect('gamification:challenges')

        # Join
        enrolment, created = ChallengeEnrolment.objects.get_or_create(
            challenge=challenge,
            employee=request.user
        )
        if created:
            messages.success(request, f"Successfully joined the challenge: {challenge.title}!")
        else:
            messages.info(request, "You are already joined in this challenge.")
            
        return redirect('gamification:challenges')


class ChallengeSubmitEvidenceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        enrolment = get_object_or_404(ChallengeEnrolment, pk=pk, employee=request.user)
        
        if enrolment.challenge.status != 'active':
            messages.error(request, "You can only submit evidence for active challenges.")
            return redirect('gamification:challenges')

        evidence_url = request.POST.get('evidence_url', '').strip()
        evidence_file = request.FILES.get('evidence_file')

        if not (evidence_url or evidence_file):
            messages.error(request, "Please provide an evidence link or upload a file.")
            return redirect('gamification:challenges')

        if evidence_url:
            enrolment.evidence_url = evidence_url
        if evidence_file:
            enrolment.evidence_file = evidence_file
            
        enrolment.submitted_at = timezone.now()
        enrolment.save()

        messages.success(request, "Evidence submitted successfully!")
        return redirect('gamification:challenges')


# 2. Badges
class BadgeListView(LoginRequiredMixin, ListView):
    model = Badge
    template_name = 'gamification/badge_list.html'
    context_object_name = 'badges'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch user's earned badge IDs
        context['earned_badges'] = BadgeAward.objects.filter(employee=self.request.user).values_list('badge_id', flat=True)
        return context


class BadgeCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Badge
    fields = ['name', 'description', 'icon', 'criteria_type', 'criteria_value', 'criteria_category', 'auto_award']
    template_name = 'gamification/badge_form.html'
    success_url = reverse_lazy('gamification:badges')
    allowed_roles = ['super_admin', 'esg_manager']


# 3. Rewards
class RewardListView(LoginRequiredMixin, ListView):
    model = Reward
    template_name = 'gamification/reward_list.html'
    context_object_name = 'rewards'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['xp_balance'] = GamificationService.get_xp_balance(self.request.user)
        return context


class RewardCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Reward
    fields = ['name', 'description', 'xp_cost', 'stock_quantity']
    template_name = 'gamification/reward_form.html'
    success_url = reverse_lazy('gamification:rewards')
    allowed_roles = ['super_admin', 'esg_manager']


class RewardRedeemView(LoginRequiredMixin, View):
    def post(self, request, pk):
        reward = get_object_or_404(Reward, pk=pk)
        try:
            GamificationService.redeem_reward(request.user, reward)
            messages.success(request, f"Successfully redeemed {reward.name}!")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('gamification:rewards')


# 4. Leaderboard View
class LeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = 'gamification/leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Employee Leaderboard (Group by user, sum XP balance from ledger or order by total XP)
        # In a real system we can sum from XPLedger. We can do:
        employees = User.objects.filter(profile__role='employee')
        employee_ranking = []
        for emp in employees:
            bal = GamificationService.get_xp_balance(emp)
            employee_ranking.append({
                'employee': emp,
                'xp': bal
            })
        # Sort descending
        employee_ranking.sort(key=lambda x: x['xp'], reverse=True)
        context['employee_leaderboard'] = employee_ranking[:10]  # top 10

        # 2. Department ESG Leaderboard
        context['dept_leaderboard'] = DepartmentESGScore.objects.select_related('department').order_by('-overall_score')

        return context

class ChallengeTransitionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ['super_admin', 'esg_manager']

    def post(self, request, pk):
        challenge = get_object_or_404(Challenge, pk=pk)
        new_status = request.POST.get('status', '').strip()

        from apps.gamification.services_lifecycle import ChallengeService
        try:
            ChallengeService.transition_challenge(challenge, new_status, actor=request.user)
            messages.success(request, f"Challenge status updated to '{new_status}' successfully!")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('gamification:challenges')
