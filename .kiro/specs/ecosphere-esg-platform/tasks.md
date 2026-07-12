# Implementation Plan: EcoSphere ESG Management Platform

## Overview

This plan implements the full EcoSphere ESG Management Platform using Django + SQLite + Tailwind CSS + Chart.js + django-allauth. Tasks are ordered to build foundational infrastructure first, then layer each module incrementally, wiring signals, services, and templates together as each app matures. Property-based tests (via Hypothesis) are placed immediately after their target implementation to catch regressions early.

---

## Tasks

- [ ] 1. Project Scaffolding and Configuration
  - [ ] 1.1 Initialize Django project and app structure
    - Run `django-admin startproject ecosphere` and create the `apps/` directory
    - Create all nine Django apps: `accounts`, `core`, `environmental`, `social`, `governance`, `gamification`, `dashboard`, `reports`, `notifications`
    - Register all apps in `INSTALLED_APPS` in `ecosphere/settings.py`
    - Configure `BASE_DIR`, `TEMPLATES`, `STATICFILES_DIRS`, `MEDIA_ROOT`, `LOGIN_URL`, `LOGIN_REDIRECT_URL`, and `LOGOUT_REDIRECT_URL`
    - Add `django-allauth`, `reportlab`, `openpyxl`, `hypothesis`, `Pillow` to `requirements.txt` and install
    - Configure `AUTHENTICATION_BACKENDS` and allauth settings (`ACCOUNT_EMAIL_REQUIRED`, `ACCOUNT_EMAIL_VERIFICATION`)
    - Add `notifications.context_processors.unread_notifications` to `TEMPLATES[0]['OPTIONS']['context_processors']`
    - _Requirements: 1.1_

  - [ ] 1.2 Create base.html, design system, and shared partials
    - Write `templates/base.html` with:
      - Dark theme (`bg-gray-950` body, `bg-gray-900` sidebar/topbar, `border-gray-800` borders)
      - Fixed left sidebar (`w-56`) with logo, grouped nav links, user role footer
      - Sticky topbar with breadcrumb, module tab pills, notification bell with unread badge
      - `{% block content %}` and `{% block scripts %}` extension points
      - Chart.js CDN and Tailwind CDN in `<head>`
      - Mobile sidebar toggle via vanilla JS
    - Write `templates/partials/sidebar_nav.html` — grouped nav links (Environmental, Social, Governance, Gamification, Reports, Settings) with role-gated Settings section
    - Write `templates/partials/module_tabs.html` — horizontal pill tabs for active module
    - Write `templates/partials/status_badge.html` — reusable colored pill: green (active/approved/completed), red (overdue), yellow (pending/in_progress), blue (draft/upcoming), gray (default)
    - Write `templates/partials/kpi_card.html` — stat card with label, value `/100`, trend text
    - Write `templates/partials/chart_card.html` — `bg-gray-900 border border-gray-800 rounded-xl` wrapper with `<canvas>` and `responsive: true, maintainAspectRatio: false`
    - Write `templates/partials/data_table.html` — dark-themed reusable table shell (`bg-gray-900`, `text-gray-400` headers, `border-gray-800` rows)
    - Write `templates/partials/pagination.html`
    - Create `static/css/custom.css` with `.nav-item`, `.nav-item.active`, `.nav-group-label` component classes
    - _Requirements: 29.1, 29.2, 29.3, 27.3_

  - [ ] 1.3 Implement per-module screen layouts (mockup-aligned)
    - **Dashboard** (`templates/dashboard/main.html`): 4-column KPI stat card row (Environmental/Social/Governance/Total ESG Score), 2-column chart row (line chart "Employee Score Trend" + bar chart "Summary ESG Ranking"), Quick Actions panel (4 colored buttons), Active Challenges summary table
    - **Environmental** (`templates/environmental/emission_list.html`): "Add New" + search bar topbar, table with inline progress bar column (`<div class="bg-green-500 h-2 rounded-full">`) and status badge column
    - **Social** (`templates/social/csr_list.html`): tab bar (All/Department/Individual), CSR Activity card grid (3–4 per row, dark cards with category pill, title, "Join" button), Employee Participation table below (Name/Department/CSR Activity/Role/Points/Approve+Reject)
    - **Governance** (`templates/governance/policy_list.html`): tab bar (Policies/Audits), Policies table with inline acknowledgement progress bar, Compliance Issues table with color-coded status rows (red=overdue, yellow=pending)
    - **Gamification challenges** (`templates/gamification/challenge_list.html`): "New Challenge" button, 3-per-row challenge cards with orange XP badge top-right, purple category pill, "Join Challenge" button; status pills by lifecycle state
    - **Badges** (`templates/gamification/badge_list.html`): 3-column card grid with centered badge icon, name, unlock rule
    - **Leaderboard** (`templates/gamification/leaderboard.html`): ranked table (Position/Name/XP/Challenges Completed/Due); top-3 rows gold/silver/bronze tinted; current user row `bg-green-500/10 border-l-2 border-green-500`
    - **Reports** (`templates/reports/report_cards.html`): 2×2 card grid (Environmental/Social/Governance/ESG Summary), each with icon, title, description, "Generate" button; Custom Report Builder section below with filter dropdowns (Module/Department/Date Range/Employee/Challenge/Category) and export buttons (View Report / Export CSV / Export Excel PDF)
    - **Settings** (`templates/core/esg_config.html`): Departments table with status pill toggles; ESG Configuration section with 3 toggle-switch rows (Enable auto emission calculator / Enable evidence for CSR activities / Enable auto badge-awarding calculator) using `peer-checked:bg-green-500` Tailwind toggle pattern
    - _Requirements: 21.1, 8.1, 9.1, 12.1, 15.1, 22.1, 4.1, 29.1, 29.3_


- [ ] 2. Authentication and Role-Based Access Control
  - [ ] 2.1 Implement `UserProfile` model and post-save signal
    - Write `accounts/models.py` with `UserProfile` (OneToOneField to `auth.User`, `role` CharField with four choices, nullable `department` FK to `core.Department`)
    - Write `accounts/signals.py` with `post_save` receiver on `User` to auto-create `UserProfile` with `role='employee'`
    - Register signal in `accounts/apps.py`
    - Create and run migrations
    - _Requirements: 1.2, 1.4_

  - [ ] 2.2 Implement `role_required` decorator and `RoleRequiredMixin`
    - Write `accounts/decorators.py` with `role_required(*roles)` — redirect to login if unauthenticated, raise `PermissionDenied` if wrong role
    - Write `accounts/mixins.py` with `RoleRequiredMixin` (class-based view equivalent)
    - _Requirements: 1.3, 1.6_

  - [ ]* 2.3 Write property test: RBAC denial (Property 1)
    - **Property 1: Role-based access denial**
    - Use Hypothesis to generate arbitrary (role, required_roles) pairs; assert HTTP 403 is returned whenever the user's role is not in the allowed set
    - **Validates: Requirements 1.3**

  - [ ]* 2.4 Write property test: Unauthenticated redirect (Property 2)
    - **Property 2: Unauthenticated redirect to login**
    - Use Hypothesis to generate arbitrary protected URL paths; assert all return a redirect to the login page when no session exists
    - **Validates: Requirements 1.6**

  - [ ]* 2.5 Write property test: Single department membership invariant (Property 3)
    - **Property 3: Single department membership invariant**
    - Use Hypothesis to generate user creation strategies; assert `UserProfile.department` never references more than one department per user
    - **Validates: Requirements 1.4**

  - [ ] 2.6 Implement login/logout templates and role-based redirect
    - Write `templates/accounts/login.html` and `templates/accounts/logout.html` extending `base.html`
    - Override allauth's `ACCOUNT_ADAPTER` or `LOGIN_REDIRECT_URL` to route users to their role-appropriate dashboard view
    - _Requirements: 1.7, 1.8_


- [ ] 3. Core Module — Department, Category, ESGConfiguration
  - [ ] 3.1 Implement `Department` and `Category` models
    - Write `core/models.py` with `Department` (`name` unique, `is_active`, `created_at`) and `Category` (`name` unique, `is_active`, `created_at`)
    - Create and run migrations
    - _Requirements: 2.1, 2.2, 3.1_

  - [ ] 3.2 Implement `ESGConfiguration` singleton model with weight validation
    - Add `ESGConfiguration` to `core/models.py` with `env_weight`, `social_weight`, `gov_weight` DecimalFields and `clean()` enforcing sum-to-100
    - Override `save()` to call `full_clean()` (enforces weight validation) and delete any pre-existing `ESGConfiguration` row before inserting — this enforces the singleton constraint at the DB level rather than relying on `.first()` sort order
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_

  - [ ]* 3.3 Write property test: ESG weight validation (Property 4)
    - **Property 4: ESG weight validation**
    - Use Hypothesis `floats` / `decimals` strategy to generate triples `(e, s, g)`; assert `ESGConfiguration.clean()` raises `ValidationError` if and only if `e + s + g ≠ 100`
    - **Validates: Requirements 4.3, 4.4**

  - [ ] 3.4 Implement Department and Category CRUD views and templates
    - Write `core/views.py` with `DepartmentListView`, `DepartmentCreateView`, `DepartmentUpdateView` (all gated to `super_admin`)
    - Write `CategoryListView`, `CategoryCreateView`, `CategoryUpdateView` (gated to `super_admin`, `esg_manager`)
    - Write `ESGConfigurationUpdateView` (gated to `super_admin`) — renders a form; on save calls `recalculate_all_departments`
    - Write `core/urls.py` and register under `core/` in `ecosphere/urls.py`
    - Write templates: `core/department_list.html`, `core/department_form.html`, `core/category_list.html`, `core/category_form.html`, `core/esg_config.html`
    - _Requirements: 2.1, 2.5, 3.1, 3.3, 4.1_


- [ ] 4. Environmental Module
  - [ ] 4.1 Implement `EmissionFactor`, `CarbonEmission`, and `SustainabilityGoal` models
    - Write `environmental/models.py` with all three models as specified in the design
    - Add `CheckConstraint(coefficient__gt=0)` on `EmissionFactor`
    - Implement `CarbonEmission.save()` to compute `co2e_value = activity_value × emission_factor.coefficient`
    - Implement `SustainabilityGoal.progress_percentage` property
    - Create and run migrations
    - _Requirements: 5.2, 6.2, 7.1, 7.2_

  - [ ]* 4.2 Write property test: CO₂e calculation correctness (Property 6)
    - **Property 6: Carbon emission CO₂e calculation**
    - Use Hypothesis `decimals(min_value=0.0001)` for `activity_value` and `coefficient`; save a `CarbonEmission` and assert `co2e_value == activity_value × coefficient` within 4 decimal places
    - **Validates: Requirements 6.2**

  - [ ]* 4.3 Write property test: Sustainability goal progress percentage (Property 8)
    - **Property 8: Sustainability goal progress percentage**
    - Use Hypothesis to generate `(current_value, target_value)` pairs with positive `target_value`; assert `progress_percentage == min((current_value / target_value) * 100, 100)`
    - **Validates: Requirements 7.3**

  - [ ] 4.4 Implement auto-recalculation signal for `EmissionFactor` coefficient changes
    - Write the `on_emission_factor_change` receiver in `dashboard/signals.py` (alongside the other ESG recalculation signals), not `environmental/signals.py`
    - The receiver queries `CarbonEmission.objects.filter(emission_factor=instance, auto_recalculate=True)` and updates `co2e_value` and `updated_at` using `save(update_fields=...)`
    - Register signal in `dashboard/apps.py`
    - _Requirements: 6.3, 6.4_

  - [ ]* 4.5 Write property test: Auto-recalculation on factor change (Property 7)
    - **Property 7: Auto-recalculation on factor coefficient change**
    - Use Hypothesis to generate emissions with `auto_recalculate=True`; update the factor's coefficient and assert each emission's `co2e_value` equals `activity_value × new_coefficient`
    - **Validates: Requirements 6.3, 6.4**

  - [ ] 4.6 Implement `check_overdue` management command (sustainability goals portion)
    - Write `environmental/management/commands/check_overdue.py` (or the combined `governance/management/commands/check_overdue.py`)
    - Logic: update `SustainabilityGoal` status to `overdue` where deadline passed and target not met; update to `completed` where `current_value >= target_value`
    - _Requirements: 7.4, 7.5_

  - [ ]* 4.7 Write property test: Sustainability goal status transitions (Property 9)
    - **Property 9: Sustainability goal status transitions**
    - Use Hypothesis to generate goals with varied `(current_value, target_value, deadline)` tuples; run the status-check logic and assert `completed` iff `current_value >= target_value`, else `overdue` if deadline passed
    - **Validates: Requirements 7.4, 7.5**

  - [ ] 4.8 Implement Environmental CRUD views and Environmental Dashboard
    - Write `environmental/views.py` with `EmissionFactorListView`, `EmissionFactorCreateView`, `EmissionFactorUpdateView` (gated to `super_admin`, `esg_manager`)
    - Write `CarbonEmissionListView`, `CarbonEmissionCreateView`, `CarbonEmissionUpdateView` (gated to `super_admin`, `esg_manager`, `dept_head`)
    - Write `SustainabilityGoalListView`, `SustainabilityGoalCreateView`, `SustainabilityGoalUpdateView` (gated to `super_admin`, `esg_manager`)
    - Write `EnvironmentalDashboardView` — scopes data by department for `dept_head`/`employee`; serialises Chart.js data for time-series, dept ranking, goal progress charts
    - Write `environmental/urls.py` and register under `environmental/`
    - Write templates: `environmental/emission_factor_list.html`, `environmental/emission_list.html`, `environmental/emission_form.html`, `environmental/goal_list.html`, `dashboard/environmental.html`
    - _Requirements: 5.1, 5.3, 6.1, 6.5, 6.6, 7.6, 8.1, 8.2, 8.3, 8.4, 8.5_


- [ ] 5. Social Module
  - [ ] 5.1 Implement `CSRActivity`, `CSRParticipation`, `DiversityMetric`, `Training`, `TrainingCompletion` models
    - Write `social/models.py` with all five models as specified in the design
    - Add `unique_together = ('activity', 'employee')` on `CSRParticipation` and `('training', 'employee')` on `TrainingCompletion`
    - Create and run migrations
    - _Requirements: 9.1, 10.1, 11.1_

  - [ ] 5.2 Implement CSR Activity CRUD views with status lifecycle
    - Write `social/views.py` with `CSRActivityListView`, `CSRActivityCreateView`, `CSRActivityUpdateView` (gated to `super_admin`, `esg_manager`, `dept_head`)
    - Implement `CSRActivityEnrolView` for employees — enforce `max_participants` cap and `activity.status == 'active'`
    - Implement `CSRParticipationSubmitView` — set status to `pending_review`, handle evidence upload when `requires_evidence=True`
    - Implement `CSRParticipationApproveView` (gated to `esg_manager`, `dept_head`) — set status to `approved`, call `GamificationService.award_xp`
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [ ]* 5.3 Write property test: CSR enrolment capacity enforcement (Property 10)
    - **Property 10: CSR enrolment capacity enforcement**
    - Use Hypothesis to generate activities with `max_participants` in range `[1, 50]`; fill to capacity then attempt one more enrolment; assert the final count remains equal to `max_participants`
    - **Validates: Requirements 9.9**

  - [ ] 5.4 Implement Diversity Metric and Training CRUD views
    - Write views for `DiversityMetricListView`, `DiversityMetricCreateView`, `TrainingListView`, `TrainingCreateView`, `TrainingCompletionUpdateView`
    - Gating: `super_admin`, `esg_manager`, `dept_head`
    - Write `social/urls.py` and register under `social/`
    - _Requirements: 10.1, 11.1, 11.2_

  - [ ] 5.5 Implement Social Dashboard
    - Write `SocialDashboardView` in `dashboard/views.py` (or `social/views.py`) — serialise CSR participation rates, training completion rates, diversity charts for Chart.js
    - Write `templates/dashboard/social.html` with bar chart for CSR rates, pie chart for diversity, training completion rate per department
    - _Requirements: 10.2, 11.3_


- [ ] 6. Governance Module
  - [ ] 6.1 Implement `ESGPolicy`, `PolicyAcknowledgement`, `Audit`, `ComplianceIssue` models
    - Write `governance/models.py` with all four models as specified in the design
    - Add `unique_together = ('policy', 'employee')` on `PolicyAcknowledgement`
    - Add `department = models.ForeignKey('core.Department', on_delete=models.PROTECT, related_name='audits')` to the `Audit` model — this is required for per-department audit completion rates in the governance score calculation
    - Create and run migrations
    - _Requirements: 12.1, 13.1, 14.1_

  - [ ] 6.2 Implement ESG Policy CRUD views with versioning and acknowledgement tracking
    - Write `governance/views.py` with `ESGPolicyListView`, `ESGPolicyCreateView`, `ESGPolicyPublishView`, `ESGPolicyNewVersionView`
    - On publish: set status to `active`, send `POLICY_PUBLISHED` notification to relevant employees via `NotificationService`
    - On new version: set parent policy status to `superseded`, delete existing `PolicyAcknowledgement` records for that policy, send `POLICY_PUBLISHED` notification
    - Write `PolicyAcknowledgeView` for employees
    - _Requirements: 12.2, 12.3, 12.4, 12.5, 12.6_

  - [ ] 6.3 Implement Audit CRUD views
    - Write `AuditListView`, `AuditCreateView`, `AuditUpdateView` (gated to `super_admin`, `esg_manager`)
    - Ensure `AuditCreateView` and `AuditUpdateView` include the `department` field in the form so each audit is scoped to a department
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 6.4 Implement Compliance Issue CRUD views with overdue flagging
    - Write `ComplianceIssueListView`, `ComplianceIssueCreateView`, `ComplianceIssueUpdateView`
    - On create: send `COMPLIANCE_ASSIGNED` notification to `issue.owner`
    - On status update to `resolved`: record `resolved_at = timezone.now()`
    - Extend `check_overdue` management command to flag overdue `ComplianceIssue` records and send `COMPLIANCE_OVERDUE` notifications
    - Write `governance/urls.py` and register under `governance/`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ] 6.5 Implement Governance Dashboard
    - Write `GovernanceDashboardView` — serialise policy acknowledgement rates, audit completion doughnut, compliance issue resolution data
    - Write `templates/dashboard/governance.html` with doughnut chart for audit ratio, overdue issues callout, policy ack rates
    - _Requirements: 12.5, 13.4, 14.4, 14.6_


- [ ] 7. Gamification Module
  - [ ] 7.1 Implement `Challenge`, `ChallengeEnrolment`, `XPLedger`, `Badge`, `BadgeAward`, `Reward`, `RedemptionTransaction` models
    - Write `gamification/models.py` with all seven models as specified in the design
    - Add `unique_together` constraints on `ChallengeEnrolment` and `BadgeAward`
    - Create and run migrations
    - _Requirements: 15.1, 15.2, 16.3, 17.1, 18.1_

  - [ ] 7.2 Implement `GamificationService.award_xp` with atomic XP ledger writes
    - Write `gamification/services.py` with `award_xp` — use `@transaction.atomic`, compute `balance_after` from last ledger entry, create `XPLedger` record
    - Implement `get_xp_balance` helper
    - _Requirements: 16.1, 16.2, 16.3_

  - [ ]* 7.3 Write property test: XP award correctness (Property 11)
    - **Property 11: XP award correctness**
    - Use Hypothesis to generate sequences of positive XP award amounts; assert that after each award the employee's `balance_after` equals the running sum, and each `XPLedger` entry has the correct `amount` and `source`
    - **Validates: Requirements 16.1, 16.2, 16.3**

  - [ ] 7.4 Implement `GamificationService.redeem_reward` with stock management
    - Implement `redeem_reward` in `gamification/services.py` — check balance and stock, call `award_xp` with negative amount, decrement stock, set `is_out_of_stock` when stock reaches zero, create `RedemptionTransaction`
    - _Requirements: 18.3, 18.4, 18.5, 18.6_

  - [ ]* 7.5 Write property test: Reward redemption gate (Property 12)
    - **Property 12: Reward redemption gate**
    - Use Hypothesis to generate `(balance, xp_cost, stock)` triples; assert redemption succeeds iff `balance >= xp_cost AND stock > 0`; assert on success balance decreases by `xp_cost` and stock decreases by 1; assert on failure both are unchanged
    - **Validates: Requirements 18.3, 18.4, 18.5**

  - [ ] 7.6 Implement Challenge lifecycle state machine and `ChallengeService`
    - Write `ChallengeService.transition_challenge` enforcing `VALID_TRANSITIONS` dict
    - Write `update_challenge_status` management command that transitions Active challenges past their `end_date` to `Under Review`
    - On activation: send `CHALLENGE_STATUS` notification to eligible employees
    - On completion: call `GamificationService.award_xp` for all enrolled employees
    - On archive: prevent further enrolments
    - _Requirements: 15.2, 15.3, 15.4, 15.5, 15.6_

  - [ ] 7.7 Implement Challenge and Reward CRUD views and enrolment/submission flow
    - Write `gamification/views.py` with `ChallengeListView`, `ChallengeCreateView`, `ChallengeTransitionView`, `ChallengeEnrolView`, `ChallengeSubmitEvidenceView`
    - Write `BadgeListView`, `BadgeCreateView`, `RewardListView`, `RewardCreateView`, `RewardRedeemView`, `LeaderboardView`
    - Write `gamification/urls.py` and register under `gamification/`
    - Write templates: `gamification/challenge_list.html`, `gamification/leaderboard.html`, `gamification/badge_list.html`, `gamification/reward_list.html`
    - _Requirements: 15.7, 15.8, 17.4, 18.2, 19.1, 19.2, 19.3, 19.5_

  - [ ] 7.8 Implement `GamificationService.evaluate_badges_for` auto-award engine
    - Implement badge evaluation for `xp_threshold`, `challenges_completed`, and `category_participation` criteria types
    - For `category_participation` badge criteria, use `ChallengeEnrolment.objects.filter(employee=employee, challenge__category=badge.criteria_category, challenge__status='completed').count()` — do NOT count XPLedger entries, which ignores category
    - Call `evaluate_badges_for` from `award_xp` after each XP credit
    - Send `BADGE_UNLOCKED` notification on award
    - _Requirements: 17.2, 17.3, 17.5_


- [ ] 8. ESG Score Calculation Engine
  - [ ] 8.1 Implement `dashboard/models.py` with `DepartmentESGScore` snapshot model
    - Write `DepartmentESGScore` with `OneToOneField(Department)`, four score fields, and `last_calculated_at`
    - Create and run migrations
    - _Requirements: 20.1, 20.7_

  - [ ] 8.2 Implement `dashboard/services.py` — all four score functions
    - Write `calculate_environmental_score(department)` — average `progress_percentage` across active/completed goals; return `Decimal('50')` if no goals
    - Write `calculate_social_score(department)` — weighted average of CSR rate (40%), training rate (40%), diversity presence (20%)
    - Write `calculate_governance_score(department)` — weighted average of policy ack rate (40%), audit completion (30%), issue resolution (30%)
    - Write `recalculate_department_esg(department)` — reads `ESGConfiguration`, applies weights, calls `update_or_create` on `DepartmentESGScore`
    - Write `recalculate_all_departments()` — iterates all active departments
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6_

  - [ ]* 8.3 Write property test: ESG score bounded weighted sum (Property 13)
    - **Property 13: ESG score is a bounded weighted sum**
    - Use Hypothesis to generate `(e, s, g)` triples in `[0, 100]` and weight triples `(we, ws, wg)` summing to 100; assert `overall_score == (e*we + s*ws + g*wg) / 100` and result is within `[0, 100]`
    - **Validates: Requirements 20.1, 20.3**

  - [ ]* 8.4 Write property test: Weight update triggers full recalculation (Property 5)
    - **Property 5: Weight update triggers full recalculation**
    - Use Hypothesis to generate weight triples summing to 100; save an `ESGConfiguration` with those weights and assert every active department's `DepartmentESGScore.overall_score` is recalculated using the new weights
    - **Validates: Requirements 4.5**

  - [ ] 8.5 Wire ESG score recalculation signals in `dashboard/signals.py`
    - Write `post_save` receivers for all ESG-affecting models, each calling the appropriate recalculation function:
      - `CarbonEmission` post_save → `recalculate_department_esg(dept)`
      - `SustainabilityGoal` post_save → `recalculate_department_esg(dept)`
      - `CSRParticipation` post_save → `recalculate_department_esg(dept)`
      - `TrainingCompletion` post_save → `recalculate_department_esg(dept)`
      - `PolicyAcknowledgement` post_save → `recalculate_department_esg(instance.employee.profile.department)`
      - `Audit` post_save → `recalculate_department_esg(instance.department)`
      - `ComplianceIssue` post_save → `recalculate_department_esg(instance.department)`
      - `ESGConfiguration` post_save → `recalculate_all_departments()`
      - `EmissionFactor` post_save → cascade `co2e_value` recalc on linked `CarbonEmission` records with `auto_recalculate=True` (Property 7 implementation)
    - Register all signals in `dashboard/apps.py`
    - _Requirements: 20.2, 4.5_

- [ ] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 10. Main Dashboard
  - [ ] 10.1 Implement `MainDashboardView` with role-scoped data
    - Write `dashboard/views.py` with `MainDashboardView` extending `LoginRequiredMixin`, `TemplateView`
    - Scope `DepartmentESGScore` queryset to the user's department when role is `dept_head` or `employee`
    - Serialise grouped bar chart data (all component scores per department) and doughnut chart data (org-level component proportions) as JSON via `DjangoJSONEncoder`
    - Include open compliance issues count, active challenges count, upcoming CSR activities count in context
    - Write `dashboard/urls.py` with `path('', MainDashboardView.as_view(), name='dashboard')`; register in project `urls.py`
    - Write `templates/dashboard/main.html` with grouped bar Chart.js, doughnut Chart.js, department ESG leaderboard table, summary widgets
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_


- [ ] 11. Notification System
  - [ ] 11.1 Implement `Notification`, `NotificationPreference`, `PlatformNotificationConfig` models
    - Write `notifications/models.py` with `NotificationEvent` TextChoices enum, `Notification`, `NotificationPreference` (`unique_together = ('user', 'event_type')`), and `PlatformNotificationConfig`
    - Create and run migrations
    - _Requirements: 27.1, 27.5, 27.6, 27.7, 28.1, 28.3_

  - [ ] 11.2 Implement `NotificationService` with in-app and email delivery
    - Write `notifications/services.py` with `NotificationService.send(recipients, event_type, title, message)` — always create `Notification`; send email only when both platform config and user preference allow
    - _Requirements: 27.1, 27.2, 27.7_

  - [ ]* 11.3 Write property test: Notification email preference enforcement (Property 16)
    - **Property 16: Notification email preference enforcement**
    - Use Hypothesis to generate user/event-type pairs; set user preference `email_enabled=False`; call `NotificationService.send` and assert no email is dispatched (mock `send_mail`) while in-app `Notification` record IS created
    - **Validates: Requirements 27.7, 28.2**

  - [ ] 11.4 Implement unread count context processor and notification bell
    - Write `notifications/context_processors.py` with `unread_notifications(request)` returning `{'unread_count': ...}`
    - Ensure `base.html` renders `{{ unread_count }}` badge on the notification bell link
    - _Requirements: 27.3_

  - [ ]* 11.5 Write property test: Notification unread count accuracy (Property 14)
    - **Property 14: Notification unread count accuracy**
    - Use Hypothesis to generate sets of read/unread notifications for a user; call the context processor and assert `unread_count` equals the exact count of `is_read=False` records
    - **Validates: Requirements 27.3**

  - [ ] 11.6 Implement notification list view, mark-read view, and settings view
    - Write `notifications/views.py` with `NotificationListView`, `NotificationMarkReadView`, `NotificationSettingsView`
    - `NotificationMarkReadView`: set `is_read=True` and `read_at=timezone.now()`
    - Write `notifications/urls.py` and register under `notifications/`
    - Write templates: `notifications/list.html`, `notifications/settings.html`
    - _Requirements: 27.4, 27.5, 28.1, 28.2_

  - [ ]* 11.7 Write property test: Notification read state transition (Property 15)
    - **Property 15: Notification read state transition**
    - Use Hypothesis to generate batches of unread notifications; POST to the mark-read endpoint for one; assert `is_read=True` for that notification and `unread_count` decreases by exactly 1
    - **Validates: Requirements 27.4**


- [ ] 12. Reports Module
  - [ ] 12.1 Implement `CustomReportAudit` model and `reports` app setup
    - Write `reports/models.py` with `CustomReportAudit` (generated_by FK, modules JSONField, date_from, date_to, departments M2M, export_format, generated_at)
    - Create and run migrations
    - _Requirements: 26.4_

  - [ ] 12.2 Implement `ReportService` — data builders for all four report types
    - Write `reports/services.py` with `ReportService.build_environmental`, `build_social`, `build_governance`, `build_esg_summary` — each returns a `{'rows': [...], ...}` dict
    - Implement `export_csv`, `export_excel`, `export_pdf` static methods using `csv`, `openpyxl`, and `reportlab`
    - _Requirements: 22.1, 22.2, 23.1, 23.2, 24.1, 24.2, 25.1, 25.2_

  - [ ] 12.3 Implement standard report views (Environmental, Social, Governance, ESG Summary)
    - Write `reports/views.py` with `EnvironmentalReportView`, `SocialReportView`, `GovernanceReportView`, `ESGSummaryReportView`
    - Each view: render a filter form (date range, departments); on POST call the appropriate `ReportService.build_*`, then call the selected export method and return `HttpResponse` with correct `Content-Type` and `Content-Disposition`
    - Gating: `super_admin`, `esg_manager`
    - _Requirements: 22.3, 23.3, 24.3, 25.3_

  - [ ] 12.4 Implement Custom Report Builder view with audit logging
    - Write `CustomReportBuilderView` — render `CustomReportForm` (modules checkboxes, date range, department multi-select, format radio); on POST, build and merge selected modules, save `CustomReportAudit`, stream file download
    - Write `reports/urls.py` and register under `reports/`
    - Write `templates/reports/builder.html`
    - _Requirements: 26.1, 26.2, 26.3, 26.4_


- [ ] 13. Management Commands
  - [ ] 13.1 Finalize `check_overdue` management command
    - Write the complete `governance/management/commands/check_overdue.py` (or merged command) handling both `SustainabilityGoal` status updates and `ComplianceIssue` overdue flagging with `NotificationService.send` calls
    - _Requirements: 7.4, 7.5, 14.3_

  - [ ] 13.2 Implement `update_challenge_status` management command
    - Write `gamification/management/commands/update_challenge_status.py`
    - Query all `Challenge` records with `status='active'` and `end_date < today`; call `ChallengeService.transition_challenge(challenge, 'under_review', actor=None)` for each
    - _Requirements: 15.4_

- [ ] 14. Mobile-Responsive Templates Pass
  - [ ] 14.1 Audit and complete all module list/form templates for mobile responsiveness
    - Ensure every list, form, and detail template extends `base.html` and uses Tailwind responsive utility classes (`sm:`, `md:`, `lg:`)
    - Ensure all form inputs and buttons have `min-h-[44px] min-w-[44px]` classes for touch target compliance
    - _Requirements: 29.1, 29.4_

  - [ ] 14.2 Implement mobile collapsible navigation in `base.html`
    - Add JavaScript toggle (vanilla JS or Alpine.js via CDN) to `base.html` that shows/hides `#mobile-menu` when `#nav-toggle` is clicked
    - Ensure nav is `hidden md:flex` on desktop and visible on mobile after toggle
    - _Requirements: 29.2_

  - [ ] 14.3 Ensure all Chart.js instances use `responsive: true, maintainAspectRatio: false`
    - Review all `<script>` blocks and `chart_card.html` partials to confirm `responsive: true` and `maintainAspectRatio: false` are set in chart options
    - Wrap each `<canvas>` in a `div` with `relative h-64` (or similar Tailwind height class) so Chart.js can size correctly
    - _Requirements: 29.3_

- [ ] 15. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 16. Wire Everything Together
  - [ ] 16.1 Connect all `apps.py` `ready()` hooks and verify signal registration
    - Confirm every app's `AppConfig.ready()` imports its `signals` module
    - Smoke-test signal chain: save a `CarbonEmission` and assert `DepartmentESGScore` is updated; update `ESGConfiguration` and assert all department scores are recalculated
    - _Requirements: 20.2, 4.5_

  - [ ] 16.2 Wire project-level `ecosphere/urls.py` and verify all URL namespaces
    - Confirm all nine app URL confs are included with correct prefixes and `app_name` namespaces
    - Verify `LOGIN_URL`, `LOGIN_REDIRECT_URL`, and allauth URLs are correctly registered
    - _Requirements: 1.6, 1.7_

  - [ ] 16.3 Create Django admin registrations for all models
    - Register all models in each app's `admin.py` with appropriate `list_display`, `list_filter`, and `search_fields` for maintainability
    - _Requirements: 1.1 (admin interface)_

- [ ] 17. Final Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints (tasks 9, 15, 17) ensure incremental validation across major milestones
- Property tests use the `hypothesis` library; install with `pip install hypothesis`
- The `check_overdue` and `update_challenge_status` commands should be scheduled via cron (e.g., `0 0 * * * python manage.py check_overdue`)
- All views use class-based views with `LoginRequiredMixin` + `RoleRequiredMixin`; function-based views may use `@login_required` + `@role_required`
- Report export views return streaming `HttpResponse` with appropriate MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `text/csv`
- Tailwind CSS is loaded via CDN in `base.html`; replace with compiled output before production deployment


## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.4", "8.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "2.6", "3.3", "4.1", "5.1", "6.1", "7.1", "11.1", "12.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "5.2", "6.2", "7.2", "8.2", "11.2"] },
    { "id": 5, "tasks": ["4.5", "4.6", "5.3", "5.4", "6.3", "6.4", "7.3", "7.4", "8.3", "8.4", "11.4"] },
    { "id": 6, "tasks": ["4.7", "4.8", "5.5", "6.5", "7.5", "7.6", "8.5", "11.3", "11.5", "11.6", "12.2"] },
    { "id": 7, "tasks": ["7.7", "7.8", "10.1", "11.7", "12.3", "13.1", "13.2"] },
    { "id": 8, "tasks": ["8.4", "12.4", "14.1", "14.2", "14.3"] },
    { "id": 9, "tasks": ["16.1", "16.2", "16.3"] }
  ]
}
```
