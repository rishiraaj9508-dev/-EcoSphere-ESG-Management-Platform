# Design Document

## EcoSphere ESG Management Platform

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Django Project Layout](#django-project-layout)
3. [Data Models](#data-models)
4. [URL Routing and Views Architecture](#url-routing-and-views-architecture)
5. [Template Structure](#template-structure)
6. [ESG Score Calculation Logic](#esg-score-calculation-logic)
7. [Notification Delivery System](#notification-delivery-system)
8. [Report Generation and Export Pipeline](#report-generation-and-export-pipeline)
9. [Gamification Engine](#gamification-engine)
10. [Chart.js Integration](#chartjs-integration)
11. [Correctness Properties](#correctness-properties)

---

## Architecture Overview

EcoSphere is structured as a Django monolith with multiple focused Django apps, SQLite as the database, Tailwind CSS (via CDN or django-tailwind) for styling, Chart.js for visualisations, and django-allauth for authentication.

```
Browser  ←→  Django (Views + Templates)  ←→  SQLite
                    ↕
              Django ORM / Services
                    ↕
          Background Tasks (Django signals + cron)
```

Key architectural decisions:

- **Service layer**: Business logic (ESG score calculation, XP awarding, badge evaluation) lives in `services.py` files within each app, not in views or models. This keeps views thin and logic testable.
- **Signals**: Django signals wire side-effects (recalculation, notifications, badge evaluation) to model save events.
- **RBAC via decorators**: A custom `role_required` decorator wraps views; a `UserProfile` model extends `auth.User` with role and department.
- **Reports**: Generated synchronously for small datasets; `openpyxl`, `reportlab`, and Python's `csv` module handle exports.
- **Gamification engine**: A `GamificationService` handles XP ledger writes, badge evaluation, and reward stock management.

---

## Django Project Layout

```
ecosphere/                          # Django project root
├── manage.py
├── ecosphere/                      # Project package
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/                   # User auth, RBAC, UserProfile
│   ├── core/                       # Department, Category, ESGConfig, shared utils
│   ├── environmental/              # EmissionFactor, CarbonEmission, SustainabilityGoal
│   ├── social/                     # CSRActivity, DiversityMetric, Training
│   ├── governance/                 # ESGPolicy, Audit, ComplianceIssue
│   ├── gamification/               # Challenge, XPLedger, Badge, Reward, Leaderboard
│   ├── dashboard/                  # Main dashboard views, ESG score aggregation
│   ├── reports/                    # Report builder, PDF/Excel/CSV export
│   └── notifications/              # Notification model, delivery, settings
├── templates/
│   ├── base.html
│   ├── accounts/
│   ├── core/
│   ├── environmental/
│   ├── social/
│   ├── governance/
│   ├── gamification/
│   ├── dashboard/
│   ├── reports/
│   └── notifications/
├── static/
│   ├── css/           # Tailwind output
│   ├── js/            # Chart.js, custom JS
│   └── img/           # Badge icons, logos
└── requirements.txt
```

---

## Data Models

### accounts app

```python
# accounts/models.py

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('esg_manager', 'ESG Manager'),
        ('dept_head',   'Department Head'),
        ('employee',    'Employee'),
    ]
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.ForeignKey('core.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='members')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # OneToOneField already enforces one profile per user;
            # department FK is nullable (Super Admin / ESG Manager span all depts)
        ]

    def __str__(self):
        return f"{self.user.username} ({self.role})"
```

### core app

```python
# core/models.py

class Department(models.Model):
    name       = models.CharField(max_length=150, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ESGConfiguration(models.Model):
    """Singleton — only one active record permitted. Singleton enforced via save() override — use ESGConfiguration.objects.first() to retrieve."""
    env_weight  = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
    social_weight = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    gov_weight  = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    updated_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ESG Configuration'

    def clean(self):
        total = self.env_weight + self.social_weight + self.gov_weight
        if total != 100:
            raise ValidationError("ESG weights must sum to exactly 100.")

    def save(self, *args, **kwargs):
        self.full_clean()  # enforces weight sum validation
        if not self.pk:
            # Delete any existing configuration before creating a new one
            ESGConfiguration.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)
```

### environmental app

```python
# environmental/models.py

class EmissionFactor(models.Model):
    name        = models.CharField(max_length=150)
    unit        = models.CharField(max_length=50)  # e.g. kWh, km, litre
    coefficient = models.DecimalField(max_digits=12, decimal_places=6)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(coefficient__gt=0), name='emission_factor_positive')
        ]


class CarbonEmission(models.Model):
    department       = models.ForeignKey('core.Department', on_delete=models.PROTECT, related_name='emissions')
    emission_source  = models.CharField(max_length=200)
    activity_value   = models.DecimalField(max_digits=14, decimal_places=4)
    emission_factor  = models.ForeignKey(EmissionFactor, on_delete=models.PROTECT, related_name='emissions')
    co2e_value       = models.DecimalField(max_digits=14, decimal_places=4, editable=False)
    auto_recalculate = models.BooleanField(default=True)
    reporting_period = models.DateField()  # YYYY-MM-01 convention for monthly periods
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.co2e_value = self.activity_value * self.emission_factor.coefficient
        super().save(*args, **kwargs)


class SustainabilityGoal(models.Model):
    STATUS_CHOICES = [('active','Active'),('overdue','Overdue'),('completed','Completed')]
    SCOPE_CHOICES  = [('org','Organization-wide'),('dept','Department-specific')]

    title          = models.CharField(max_length=200)
    target_metric  = models.CharField(max_length=150)
    target_value   = models.DecimalField(max_digits=14, decimal_places=4)
    current_value  = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit           = models.CharField(max_length=50)
    deadline       = models.DateField()
    scope          = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    department     = models.ForeignKey('core.Department', null=True, blank=True, on_delete=models.SET_NULL)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def progress_percentage(self):
        if self.target_value == 0:
            return 0
        return min(float(self.current_value / self.target_value * 100), 100)
```

### social app

```python
# social/models.py

class CSRActivity(models.Model):
    STATUS_CHOICES = [('upcoming','Upcoming'),('active','Active'),('closed','Closed')]

    title             = models.CharField(max_length=200)
    description       = models.TextField()
    category          = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True)
    department        = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    start_date        = models.DateField()
    end_date          = models.DateField()
    max_participants  = models.PositiveIntegerField()
    requires_evidence = models.BooleanField(default=False)
    xp_reward         = models.PositiveIntegerField(default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at        = models.DateTimeField(auto_now_add=True)


class CSRParticipation(models.Model):
    STATUS_CHOICES = [('enrolled','Enrolled'),('pending_review','Pending Review'),('approved','Approved'),('rejected','Rejected')]

    activity     = models.ForeignKey(CSRActivity, on_delete=models.CASCADE, related_name='participations')
    employee     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evidence_url = models.URLField(blank=True)
    evidence_file= models.FileField(upload_to='csr_evidence/', blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    reviewed_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reviewed_participations')

    class Meta:
        unique_together = ('activity', 'employee')


class DiversityMetric(models.Model):
    department       = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    metric_type      = models.CharField(max_length=100)  # gender_ratio, age_group, etc.
    value            = models.DecimalField(max_digits=10, decimal_places=4)
    unit             = models.CharField(max_length=50)
    reporting_period = models.DateField()
    created_at       = models.DateTimeField(auto_now_add=True)


class Training(models.Model):
    title         = models.CharField(max_length=200)
    department    = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    training_date = models.DateField()
    created_at    = models.DateTimeField(auto_now_add=True)


class TrainingCompletion(models.Model):
    training  = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='completions')
    employee  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('training', 'employee')
```

### governance app

```python
# governance/models.py

class ESGPolicy(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('active','Active'),('superseded','Superseded')]

    title          = models.CharField(max_length=200)
    description    = models.TextField()
    category       = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True)
    version        = models.CharField(max_length=20)
    effective_date = models.DateField()
    review_cycle   = models.PositiveIntegerField(help_text='Review cycle in days')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    parent_policy  = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='versions')
    created_at     = models.DateTimeField(auto_now_add=True)


class PolicyAcknowledgement(models.Model):
    policy       = models.ForeignKey(ESGPolicy, on_delete=models.CASCADE, related_name='acknowledgements')
    employee     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('policy', 'employee')


class Audit(models.Model):
    STATUS_CHOICES = [('planned','Planned'),('in_progress','In Progress'),('completed','Completed')]

    title           = models.CharField(max_length=200)
    department      = models.ForeignKey('core.Department', on_delete=models.PROTECT, related_name='audits')
    scope           = models.TextField()
    auditor         = models.CharField(max_length=200)
    audit_date      = models.DateField()
    findings        = models.TextField(blank=True)
    resolution_notes= models.TextField(blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)


class ComplianceIssue(models.Model):
    SEVERITY_CHOICES = [('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')]
    STATUS_CHOICES   = [('open','Open'),('in_progress','In Progress'),('resolved','Resolved')]

    title         = models.CharField(max_length=200)
    description   = models.TextField()
    department    = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    owner         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_issues')
    due_date      = models.DateField()
    severity      = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_overdue    = models.BooleanField(default=False)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
```

### gamification app

```python
# gamification/models.py

class Challenge(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('active','Active'),('under_review','Under Review'),('completed','Completed'),('archived','Archived')]

    title          = models.CharField(max_length=200)
    description    = models.TextField()
    category       = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True)
    xp_reward      = models.PositiveIntegerField()
    start_date     = models.DateField()
    end_date       = models.DateField()
    target_all     = models.BooleanField(default=True)  # True = all employees
    departments    = models.ManyToManyField('core.Department', blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)


class ChallengeEnrolment(models.Model):
    challenge        = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='enrolments')
    employee         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evidence_url     = models.URLField(blank=True)
    evidence_file    = models.FileField(upload_to='challenge_evidence/', blank=True)
    submitted_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('challenge', 'employee')


class XPLedger(models.Model):
    SOURCE_CHOICES = [('challenge','Challenge'),('csr','CSR Activity'),('badge','Badge'),('admin','Admin Award'),('redemption','Redemption')]

    employee  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_ledger')
    source    = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    reference_id = models.PositiveIntegerField(null=True, blank=True)  # FK to source object
    amount    = models.IntegerField()  # positive = earn, negative = spend
    balance_after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    note      = models.CharField(max_length=300, blank=True)


class Badge(models.Model):
    CRITERIA_CHOICES = [('xp_threshold','XP Threshold'),('challenges_completed','Challenges Completed'),('category_participation','Category Participation')]

    name           = models.CharField(max_length=100)
    description    = models.TextField()
    icon           = models.ImageField(upload_to='badges/', blank=True)
    criteria_type  = models.CharField(max_length=30, choices=CRITERIA_CHOICES)
    criteria_value = models.PositiveIntegerField()
    criteria_category = models.ForeignKey('core.Category', null=True, blank=True, on_delete=models.SET_NULL)
    auto_award     = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)


class BadgeAward(models.Model):
    badge       = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    employee    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    awarded_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='granted_badges')
    awarded_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('badge', 'employee')


class Reward(models.Model):
    name           = models.CharField(max_length=200)
    description    = models.TextField()
    xp_cost        = models.PositiveIntegerField()
    stock_quantity = models.IntegerField(default=0)
    is_out_of_stock= models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)


class RedemptionTransaction(models.Model):
    employee   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reward     = models.ForeignKey(Reward, on_delete=models.PROTECT)
    xp_spent   = models.PositiveIntegerField()
    redeemed_at= models.DateTimeField(auto_now_add=True)
```

### notifications app

```python
# notifications/models.py

class NotificationEvent(models.TextChoices):
    COMPLIANCE_ASSIGNED   = 'compliance_assigned', 'Compliance Issue Assigned'
    COMPLIANCE_OVERDUE    = 'compliance_overdue',  'Compliance Issue Overdue'
    CSR_APPROVED          = 'csr_approved',         'CSR Participation Approved'
    CHALLENGE_STATUS      = 'challenge_status',     'Challenge Status Changed'
    POLICY_PUBLISHED      = 'policy_published',     'ESG Policy Published/Updated'
    BADGE_UNLOCKED        = 'badge_unlocked',       'Badge Unlocked'
    REWARD_REDEEMED       = 'reward_redeemed',      'Reward Redemption Confirmed'


class Notification(models.Model):
    recipient   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    event_type  = models.CharField(max_length=30, choices=NotificationEvent.choices)
    title       = models.CharField(max_length=200)
    message     = models.TextField()
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    read_at     = models.DateTimeField(null=True, blank=True)


class NotificationPreference(models.Model):
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_prefs')
    event_type    = models.CharField(max_length=30, choices=NotificationEvent.choices)
    email_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'event_type')


class PlatformNotificationConfig(models.Model):
    """Singleton — Super Admin controls which event types generate emails at platform level."""
    event_type     = models.CharField(max_length=30, choices=NotificationEvent.choices, unique=True)
    email_enabled  = models.BooleanField(default=True)
```

### dashboard app — ESG Score snapshot

```python
# dashboard/models.py

class DepartmentESGScore(models.Model):
    """Cached ESG score snapshot per department, refreshed on data changes."""
    department        = models.OneToOneField('core.Department', on_delete=models.CASCADE, related_name='esg_score')
    environmental_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    social_score        = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    governance_score    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_score       = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_calculated_at  = models.DateTimeField(auto_now=True)
```

---

## URL Routing and Views Architecture

### RBAC Decorator

```python
# accounts/decorators.py

from functools import wraps
from django.core.exceptions import PermissionDenied

def role_required(*roles):
    """Usage: @role_required('super_admin', 'esg_manager')"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                from django.shortcuts import redirect
                return redirect(settings.LOGIN_URL)
            if request.user.profile.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
```

### Project URL structure (ecosphere/urls.py)

```python
urlpatterns = [
    path('admin/',         admin.site.urls),
    path('accounts/',      include('allauth.urls')),
    path('',               include('apps.dashboard.urls')),
    path('core/',          include('apps.core.urls')),
    path('environmental/', include('apps.environmental.urls')),
    path('social/',        include('apps.social.urls')),
    path('governance/',    include('apps.governance.urls')),
    path('gamification/',  include('apps.gamification.urls')),
    path('reports/',       include('apps.reports.urls')),
    path('notifications/', include('apps.notifications.urls')),
]
```

### Key View Patterns

Views are class-based (Django's `LoginRequiredMixin` + custom `RoleRequiredMixin`). Example pattern:

```python
# core/views.py

class DepartmentListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Department
    template_name = 'core/department_list.html'
    allowed_roles = ['super_admin']

    def get_queryset(self):
        return Department.objects.annotate(
            member_count=Count('members'),
        ).prefetch_related('esg_score')
```

### URL table summary

| App           | URL prefix         | Key endpoints                                          | Roles                         |
|---------------|--------------------|--------------------------------------------------------|-------------------------------|
| dashboard     | `/`                | `dashboard/`, `env-dashboard/`, `social-dashboard/`, `gov-dashboard/` | all             |
| core          | `/core/`           | `departments/`, `categories/`, `esg-config/`           | super_admin, esg_manager      |
| environmental | `/environmental/`  | `emission-factors/`, `emissions/`, `goals/`            | super_admin, esg_manager, dept_head |
| social        | `/social/`         | `csr/`, `diversity/`, `training/`                      | super_admin, esg_manager, dept_head |
| governance    | `/governance/`     | `policies/`, `audits/`, `issues/`                      | super_admin, esg_manager      |
| gamification  | `/gamification/`   | `challenges/`, `badges/`, `rewards/`, `leaderboard/`   | all (role-scoped)             |
| reports       | `/reports/`        | `environmental/`, `social/`, `governance/`, `esg-summary/`, `custom/` | super_admin, esg_manager |
| notifications | `/notifications/`  | `list/`, `mark-read/<id>/`, `settings/`                | all                           |

---

## Template Structure

### Visual Design System (from mockup)

The entire platform uses a **dark theme**. All pages share the same Tailwind color tokens:

| Token | Tailwind class | Usage |
|-------|---------------|-------|
| Page background | `bg-gray-950` | Body/page |
| Card/panel background | `bg-gray-900` | All cards, sidebar, tables |
| Card border | `border border-gray-800` | Card outlines |
| Primary accent | `bg-green-500` / `text-green-400` | Active nav, buttons, scores |
| Secondary text | `text-gray-400` | Labels, subtitles |
| Primary text | `text-white` | Headings, values |
| Danger/Overdue | `bg-red-500/20 text-red-400` | Overdue status badges |
| Warning/Pending | `bg-yellow-500/20 text-yellow-400` | Pending/In Progress badges |
| Success/Approved | `bg-green-500/20 text-green-400` | Approved/Completed badges |
| Info/Active | `bg-blue-500/20 text-blue-400` | Active status badges |
| XP/Points accent | `bg-orange-500` | XP badges, challenge reward tags |

---

### Layout: Sidebar + Main Content

All authenticated pages use a **two-column layout**: a fixed left sidebar and a scrollable main content area.

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{% block title %}EcoSphere{% endblock %} — ESG Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = { darkMode: 'class' }</script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex">

  <!-- LEFT SIDEBAR (fixed, w-56) -->
  <aside id="sidebar" class="w-56 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col fixed top-0 left-0 z-30">
    <!-- Logo -->
    <div class="px-4 py-4 border-b border-gray-800">
      <span class="text-green-400 font-bold text-lg">🌱 EcoSphere</span>
      <p class="text-gray-500 text-xs mt-0.5">ESG Management Platform</p>
    </div>
    <!-- Nav groups -->
    <nav class="flex-1 overflow-y-auto py-4 space-y-1 px-2">
      {% include 'partials/sidebar_nav.html' %}
    </nav>
    <!-- User footer -->
    <div class="px-4 py-3 border-t border-gray-800 text-xs text-gray-400">
      {{ request.user.get_full_name }}
      <span class="ml-1 px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 uppercase text-[10px]">{{ request.user.profile.role }}</span>
    </div>
  </aside>

  <!-- MAIN CONTENT (offset by sidebar width) -->
  <div class="ml-56 flex-1 flex flex-col min-h-screen">
    <!-- Top bar with breadcrumb + module tabs + notifications -->
    <header class="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between sticky top-0 z-20">
      <div>
        <p class="text-xs text-gray-500">{% block breadcrumb %}Dashboard{% endblock %}</p>
        <h1 class="text-sm font-semibold text-white">{% block page_title %}EcoSphere Dashboard{% endblock %}</h1>
      </div>
      <div class="flex items-center gap-3">
        <!-- Module tab pills -->
        {% include 'partials/module_tabs.html' %}
        <!-- Notification bell -->
        <a href="{% url 'notifications:list' %}" class="relative text-gray-400 hover:text-white">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-5-5.917V4a1 1 0 10-2 0v1.083A6 6 0 006 11v3.159c0 .538-.214 1.055-.595 1.437L4 17h5m6 0a3 3 0 11-6 0" /></svg>
          {% if unread_count %}<span class="absolute -top-1 -right-1 bg-green-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{{ unread_count }}</span>{% endif %}
        </a>
      </div>
    </header>

    <!-- Page content -->
    <main class="flex-1 px-6 py-6">
      {% block content %}{% endblock %}
    </main>
  </div>

  <!-- Mobile overlay -->
  <div id="sidebar-overlay" class="fixed inset-0 bg-black/60 z-20 hidden md:hidden"></div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  {% block scripts %}{% endblock %}
  <script>
    // Mobile sidebar toggle
    document.getElementById('nav-toggle')?.addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('-translate-x-full');
      document.getElementById('sidebar-overlay').classList.toggle('hidden');
    });
  </script>
</body>
</html>
```

### Sidebar Navigation (`templates/partials/sidebar_nav.html`)

```html
{% load sidebar_tags %}
<!-- Nav items are grouped by module, rendered only for permitted roles -->
<a href="{% url 'dashboard:main' %}" class="nav-item {% active 'dashboard' %}">🏠 Dashboard</a>

<p class="nav-group-label">Environmental</p>
<a href="{% url 'environmental:emissions' %}" class="nav-item">Emission Tracking</a>
<a href="{% url 'environmental:goals' %}" class="nav-item">Goals & Targets</a>
<a href="{% url 'environmental:dashboard' %}" class="nav-item">Env Dashboard</a>

<p class="nav-group-label">Social</p>
<a href="{% url 'social:csr' %}" class="nav-item">CSR Activities</a>
<a href="{% url 'social:diversity' %}" class="nav-item">Diversity Metrics</a>
<a href="{% url 'social:training' %}" class="nav-item">Training</a>

<p class="nav-group-label">Governance</p>
<a href="{% url 'governance:policies' %}" class="nav-item">Policies</a>
<a href="{% url 'governance:audits' %}" class="nav-item">Audits</a>
<a href="{% url 'governance:issues' %}" class="nav-item">Compliance Issues</a>

<p class="nav-group-label">Gamification</p>
<a href="{% url 'gamification:challenges' %}" class="nav-item">Challenges</a>
<a href="{% url 'gamification:badges' %}" class="nav-item">Badges</a>
<a href="{% url 'gamification:rewards' %}" class="nav-item">Rewards</a>
<a href="{% url 'gamification:leaderboard' %}" class="nav-item">Leaderboard</a>

<p class="nav-group-label">Reports</p>
<a href="{% url 'reports:environmental' %}" class="nav-item">Environmental Report</a>
<a href="{% url 'reports:social' %}" class="nav-item">Social Report</a>
<a href="{% url 'reports:governance' %}" class="nav-item">Governance Report</a>
<a href="{% url 'reports:summary' %}" class="nav-item">ESG Summary</a>
<a href="{% url 'reports:custom' %}" class="nav-item">Custom Report Builder</a>

{% if request.user.profile.role in 'super_admin,esg_manager' %}
<p class="nav-group-label">Settings</p>
<a href="{% url 'core:departments' %}" class="nav-item">Departments</a>
<a href="{% url 'core:categories' %}" class="nav-item">Categories</a>
<a href="{% url 'core:esg-config' %}" class="nav-item">ESG Configuration</a>
<a href="{% url 'notifications:settings' %}" class="nav-item">Notification Settings</a>
{% endif %}
```

Tailwind utility classes for nav items (add to `static/css/custom.css` or use `@layer components`):
```css
.nav-item { @apply flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors; }
.nav-item.active { @apply bg-green-500/10 text-green-400 font-medium; }
.nav-group-label { @apply px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider text-gray-600 font-semibold; }
```

---

### Screen Designs by Module

#### Main Dashboard (`templates/dashboard/main.html`)

Layout:
1. **4 KPI stat cards** (row) — Environmental Score, Social Score, Governance Score, Total ESG Score
2. **Two-column row**: left = line chart "Employee Score Trend", right = bar chart "Summary ESG Ranking"
3. **Quick Actions panel** (4 colored action buttons)
4. **Active Challenges list** (table with status pills)

```html
<!-- KPI stat card pattern -->
<div class="grid grid-cols-4 gap-4 mb-6">
  {% for card in kpi_cards %}
  <div class="bg-gray-900 border border-gray-800 rounded-xl p-4">
    <p class="text-xs text-gray-400 mb-1">{{ card.label }}</p>
    <p class="text-2xl font-bold text-white">{{ card.value }} <span class="text-sm text-gray-500">/ 100</span></p>
    <p class="text-xs mt-1 {{ card.trend_class }}">{{ card.trend }}</p>
  </div>
  {% endfor %}
</div>

<!-- Charts row -->
<div class="grid grid-cols-2 gap-4 mb-6">
  <div class="bg-gray-900 border border-gray-800 rounded-xl p-4">
    <h3 class="text-sm font-medium text-gray-300 mb-3">Employee Score Trend</h3>
    <div class="relative h-48"><canvas id="scoreTrendChart"></canvas></div>
  </div>
  <div class="bg-gray-900 border border-gray-800 rounded-xl p-4">
    <h3 class="text-sm font-medium text-gray-300 mb-3">Summary ESG Ranking</h3>
    <div class="relative h-48"><canvas id="esgRankingChart"></canvas></div>
  </div>
</div>
```

---

#### Environmental Module (`templates/environmental/emission_list.html`)

Layout:
- Top bar: "Add New" green button + search/filter inputs + "Export" button
- Table with columns: **Emission Source | Department | Type | CO₂ (kg) | Current CO₂ | Progress | Details | Status | Action**
- Progress column renders an inline `<div class="bg-green-500 h-2 rounded-full">` bar
- Status badge: `<span class="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400">Active</span>`
- Action: Edit / Deactivate icon buttons

```html
<!-- Reusable status badge partial -->
<!-- templates/partials/status_badge.html -->
{% if status == 'active' or status == 'approved' or status == 'completed' %}
  <span class="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400">{{ status|title }}</span>
{% elif status == 'overdue' %}
  <span class="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400">Overdue</span>
{% elif status == 'pending_review' or status == 'in_progress' %}
  <span class="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-400">{{ status|title }}</span>
{% elif status == 'draft' or status == 'upcoming' %}
  <span class="px-2 py-0.5 rounded-full text-xs bg-blue-500/20 text-blue-400">{{ status|title }}</span>
{% else %}
  <span class="px-2 py-0.5 rounded-full text-xs bg-gray-700 text-gray-400">{{ status|title }}</span>
{% endif %}
```

---

#### Social Module (`templates/social/csr_list.html`)

Layout:
- **Tabs**: All / Department / Individual (toggle tabs, active tab has green underline)
- **CSR Activity cards** (3–4 per row, card grid):
  - Dark card (`bg-gray-900 border border-gray-800 rounded-xl p-4`)
  - Category tag (colored pill, e.g. `bg-blue-500/20 text-blue-400`)
  - Activity title, description truncated to 2 lines
  - Employee avatar + name at bottom
  - "Join" button (`bg-green-500 hover:bg-green-600 text-white text-xs px-3 py-1.5 rounded-lg`)
- **Employee Participation table** below cards:
  - Columns: Name | Department | CSR Activity | Role | Points | Action
  - Action = green "Approve" + red "Reject" buttons

```html
<!-- CSR Activity card -->
<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-2">
  <span class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 w-fit">{{ activity.category }}</span>
  <h4 class="text-sm font-semibold text-white">{{ activity.title }}</h4>
  <p class="text-xs text-gray-400 line-clamp-2">{{ activity.description }}</p>
  <div class="flex items-center justify-between mt-auto pt-2">
    <span class="text-xs text-gray-500">{{ activity.department }}</span>
    <a href="{% url 'social:csr-enrol' activity.pk %}" class="bg-green-500 hover:bg-green-600 text-white text-xs px-3 py-1.5 rounded-lg">Join</a>
  </div>
</div>
```

---

#### Governance Module (`templates/governance/policy_list.html` + `issue_list.html`)

Layout:
- **Tabs**: Policies / Audits (top tab bar)
- **Policies table**: Title | Type | Status badge | Acknowledgement progress bar | Actions
  - Acknowledgement progress = inline `<div>` bar showing `ack_count / total_employees * 100%`
- **Compliance Issues table** (below or separate page):
  - Columns: ID | Description | Owner | Deadline | Date | Status badge
  - Overdue rows: status badge `bg-red-500/20 text-red-400`
  - Pending rows: `bg-yellow-500/20 text-yellow-400`

---

#### Gamification Module

**Challenges tab** (`templates/gamification/challenge_list.html`):
- "New Challenge" green button top-left
- **Challenge cards** (3 per row):
  - Dark card with title, XP badge (`bg-orange-500 text-white text-xs px-2 py-0.5 rounded`) top-right
  - Category pill, description, deadline
  - "Join Challenge" button at bottom
  - Status pill: Draft (blue) / Active (green) / Under Review (yellow) / Completed (gray) / Archived (gray)

**Badges tab** (`templates/gamification/badge_list.html`):
- 3-column card grid
- Each card: badge icon (large, centered), badge name, unlock rule description

**Leaderboard tab** (`templates/gamification/leaderboard.html`):
- Table: Position | Employee Name | XP Total | Challenges Completed | Challenges Due
- Top 3 rows highlighted with `bg-yellow-500/10` (gold), `bg-gray-500/10` (silver), `bg-orange-500/10` (bronze)
- Current user's row highlighted with `bg-green-500/10 border-l-2 border-green-500`

```html
<!-- Challenge card -->
<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-2 relative">
  <span class="absolute top-3 right-3 bg-orange-500 text-white text-xs px-2 py-0.5 rounded font-medium">{{ challenge.xp_reward }} XP</span>
  <span class="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 w-fit">{{ challenge.category }}</span>
  <h4 class="text-sm font-semibold text-white pr-12">{{ challenge.title }}</h4>
  <p class="text-xs text-gray-400 line-clamp-2">{{ challenge.description }}</p>
  <p class="text-xs text-gray-500">Deadline: {{ challenge.end_date }}</p>
  <div class="flex items-center justify-between mt-auto pt-2">
    {% include 'partials/status_badge.html' with status=challenge.status %}
    <a href="{% url 'gamification:enrol' challenge.pk %}" class="bg-green-500 hover:bg-green-600 text-white text-xs px-3 py-1.5 rounded-lg">Join Challenge</a>
  </div>
</div>
```

---

#### Reports Module (`templates/reports/`)

Layout:
- **4 report type cards** in a 2×2 grid:
  - Environmental Report, Social Policy, Governance Report, ESG Summary
  - Each card: icon, title, short description, "Generate" button
- **Custom Report Builder** section below:
  - Filter dropdowns: Module | Department | Date Range | Employee | Challenge | ESG Category
  - Export buttons: "View Report" | "Export CSV" | "Export Excel PDF"

```html
<!-- Report type card -->
<div class="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3">
  <div class="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center text-green-400 text-xl">{{ icon }}</div>
  <h4 class="text-sm font-semibold text-white">{{ title }}</h4>
  <p class="text-xs text-gray-400 flex-1">{{ description }}</p>
  <a href="{{ generate_url }}" class="bg-green-500 hover:bg-green-600 text-white text-xs px-4 py-2 rounded-lg text-center">Generate</a>
</div>
```

---

#### Settings Module (`templates/core/settings.html`)

Layout:
- **Departments table**: Name | Code | Total Unit | Head | Employee | Other | Status toggle (green/gray pill toggle)
- **ESG Configuration & Notifications** section:
  - Three toggle rows (each: label + description + on/off toggle switch):
    1. "Enable auto emission calculator" — when on, auto-calculates CO₂e from linked records
    2. "Enable evidence for CSR activities" — when on, proof file required before approval
    3. "Enable auto badge-awarding calculator" — when on, badges auto-awarded on criteria met

```html
<!-- Toggle switch component -->
<div class="flex items-center justify-between py-3 border-b border-gray-800">
  <div>
    <p class="text-sm text-white">{{ toggle.label }}</p>
    <p class="text-xs text-gray-400">{{ toggle.description }}</p>
  </div>
  <label class="relative inline-flex items-center cursor-pointer">
    <input type="checkbox" name="{{ toggle.name }}" {% if toggle.value %}checked{% endif %} class="sr-only peer">
    <div class="w-10 h-5 bg-gray-700 peer-focus:ring-2 peer-focus:ring-green-500 rounded-full peer peer-checked:bg-green-500 transition-colors"></div>
    <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
  </label>
</div>
```

---

### Shared Partial Templates

| Partial | Purpose |
|---------|---------|
| `partials/sidebar_nav.html` | Left sidebar navigation links with role filtering |
| `partials/module_tabs.html` | Top horizontal module tab pills |
| `partials/status_badge.html` | Reusable colored status badge (green/red/yellow/blue/gray) |
| `partials/kpi_card.html` | Stat card with label, value, trend |
| `partials/chart_card.html` | Chart.js canvas wrapper with dark background |
| `partials/data_table.html` | Reusable dark-themed table with thead/tbody |
| `partials/pagination.html` | Page navigation for list views |

### Template file list

```
templates/
├── base.html                          # Sidebar + topbar layout shell
├── partials/
│   ├── sidebar_nav.html
│   ├── module_tabs.html
│   ├── status_badge.html              # ← NEW: shared status pill
│   ├── kpi_card.html
│   ├── chart_card.html
│   ├── data_table.html
│   └── pagination.html
├── accounts/
│   ├── login.html
│   └── logout.html
├── dashboard/
│   ├── main.html                      # 4 KPI cards + 2 charts + quick actions
│   ├── environmental.html
│   ├── social.html
│   └── governance.html
├── environmental/
│   ├── emission_factor_list.html
│   ├── emission_list.html             # Table with inline progress bar
│   ├── emission_form.html
│   └── goal_list.html
├── social/
│   ├── csr_list.html                  # Tab view + card grid + participation table
│   ├── csr_form.html
│   ├── diversity_list.html
│   └── training_list.html
├── governance/
│   ├── policy_list.html               # Tab: Policies / Audits
│   ├── policy_form.html
│   ├── audit_list.html
│   └── issue_list.html                # Color-coded overdue/pending rows
├── gamification/
│   ├── challenge_list.html            # Card grid with XP badge, Join button
│   ├── badge_list.html                # 3-col badge card grid
│   ├── reward_list.html
│   └── leaderboard.html               # Top-3 highlighted table
├── reports/
│   ├── report_cards.html              # 2×2 generate card grid
│   └── builder.html                   # Filter dropdowns + export buttons
├── core/
│   ├── department_list.html           # Table with status toggles
│   ├── department_form.html
│   ├── category_list.html
│   ├── category_form.html
│   └── esg_config.html                # Toggle switches for 3 settings
└── notifications/
    ├── list.html
    └── settings.html
```

---

## ESG Score Calculation Logic

### Overview

ESG Score is calculated per department as a weighted sum of three normalised component scores (0–100 each):

```
ESG_Score = (env_score × env_weight/100)
          + (social_score × social_weight/100)
          + (gov_score × gov_weight/100)
```

Weights come from the single active `ESGConfiguration` record (default 40/30/30).

### Service: `dashboard/services.py`

```python
from decimal import Decimal
from apps.core.models import ESGConfiguration

def calculate_environmental_score(department) -> Decimal:
    """
    Score based on CO2e reduction progress against Sustainability Goals.
    Normalised to 0-100: average progress_percentage across active goals.
    If no goals exist, score = 50 (neutral baseline).
    """
    from apps.environmental.models import SustainabilityGoal
    goals = SustainabilityGoal.objects.filter(
        department=department, status__in=['active', 'completed']
    )
    if not goals.exists():
        return Decimal('50')
    total_progress = sum(g.progress_percentage for g in goals)
    return Decimal(str(min(total_progress / goals.count(), 100)))


def calculate_social_score(department) -> Decimal:
    """
    Weighted average of:
      - CSR participation rate (40%)
      - Training completion rate (40%)
      - Diversity metric presence score (20%)
    """
    from apps.social.models import CSRActivity, CSRParticipation, TrainingCompletion, Training, DiversityMetric
    from django.db.models import Count

    # CSR participation rate
    activities = CSRActivity.objects.filter(department=department, status='closed')
    if activities.exists():
        approved = CSRParticipation.objects.filter(activity__in=activities, status='approved').count()
        enrolled = CSRParticipation.objects.filter(activity__in=activities).count()
        csr_rate = (approved / enrolled * 100) if enrolled > 0 else 50
    else:
        csr_rate = 50

    # Training completion rate
    trainings = Training.objects.filter(department=department)
    if trainings.exists():
        completions = TrainingCompletion.objects.filter(training__in=trainings, completed=True).count()
        total = TrainingCompletion.objects.filter(training__in=trainings).count()
        training_rate = (completions / total * 100) if total > 0 else 50
    else:
        training_rate = 50

    # Diversity metric presence: simple presence score (has records = 100, else 0)
    diversity_score = 100 if DiversityMetric.objects.filter(department=department).exists() else 0

    score = (csr_rate * 0.4) + (training_rate * 0.4) + (diversity_score * 0.2)
    return Decimal(str(min(max(score, 0), 100)))


def calculate_governance_score(department) -> Decimal:
    """
    Weighted average of:
      - Policy acknowledgement completion rate (40%)
      - Audit completion ratio (30%)
      - Compliance issue resolution ratio (30%)
    """
    from apps.governance.models import ESGPolicy, PolicyAcknowledgement, Audit, ComplianceIssue
    from apps.accounts.models import UserProfile

    employees = UserProfile.objects.filter(department=department, role='employee')
    total_employees = employees.count()

    active_policies = ESGPolicy.objects.filter(status='active')
    if active_policies.exists() and total_employees > 0:
        acks = PolicyAcknowledgement.objects.filter(
            policy__in=active_policies,
            employee__in=employees.values('user')
        ).count()
        policy_rate = min((acks / (active_policies.count() * total_employees)) * 100, 100)
    else:
        policy_rate = 50

    audits = Audit.objects.filter(department=department)
    if audits.exists():
        completed_audits = audits.filter(status='completed').count()
        audit_rate = (completed_audits / audits.count()) * 100
    else:
        audit_rate = 50

    issues = ComplianceIssue.objects.filter(department=department)
    if issues.exists():
        resolved = issues.filter(status='resolved').count()
        issue_rate = (resolved / issues.count()) * 100
    else:
        issue_rate = 100  # No issues is perfect governance

    score = (policy_rate * 0.4) + (audit_rate * 0.3) + (issue_rate * 0.3)
    return Decimal(str(min(max(score, 0), 100)))


def recalculate_department_esg(department):
    """
    Recalculate and persist ESG scores for a single department.
    Called by Django signals whenever underlying data changes.
    """
    from apps.dashboard.models import DepartmentESGScore
    config = ESGConfiguration.objects.first()
    if not config:
        return

    env_score   = calculate_environmental_score(department)
    soc_score   = calculate_social_score(department)
    gov_score   = calculate_governance_score(department)

    overall = (
        env_score   * (config.env_weight / 100) +
        soc_score   * (config.social_weight / 100) +
        gov_score   * (config.gov_weight / 100)
    )

    DepartmentESGScore.objects.update_or_create(
        department=department,
        defaults={
            'environmental_score': env_score,
            'social_score': soc_score,
            'governance_score': gov_score,
            'overall_score': round(overall, 2),
        }
    )


def recalculate_all_departments():
    """Triggered when ESGConfiguration weights change."""
    from apps.core.models import Department
    for dept in Department.objects.filter(is_active=True):
        recalculate_department_esg(dept)
```

### Signal wiring

```python
# dashboard/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.environmental.models import CarbonEmission, SustainabilityGoal, EmissionFactor
from apps.social.models import CSRParticipation, TrainingCompletion
from apps.governance.models import PolicyAcknowledgement, Audit, ComplianceIssue
from apps.core.models import ESGConfiguration
from .services import recalculate_department_esg, recalculate_all_departments

@receiver(post_save, sender=CarbonEmission)
@receiver(post_save, sender=SustainabilityGoal)
def on_env_data_change(sender, instance, **kwargs):
    dept = instance.department if hasattr(instance, 'department') else None
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=CSRParticipation)
def on_social_data_change(sender, instance, **kwargs):
    recalculate_department_esg(instance.activity.department)

@receiver(post_save, sender=PolicyAcknowledgement)
def on_policy_ack_change(sender, instance, **kwargs):
    recalculate_department_esg(instance.employee.profile.department)

@receiver(post_save, sender=Audit)
def on_audit_change(sender, instance, **kwargs):
    recalculate_department_esg(instance.department)

@receiver(post_save, sender=ComplianceIssue)
def on_compliance_issue_change(sender, instance, **kwargs):
    recalculate_department_esg(instance.department)

@receiver(post_save, sender=ESGConfiguration)
def on_config_change(sender, instance, **kwargs):
    recalculate_all_departments()

@receiver(post_save, sender=EmissionFactor)
def on_emission_factor_change(sender, instance, **kwargs):
    """
    When an EmissionFactor coefficient changes, recalculate co2e_value
    for all CarbonEmission records with auto_recalculate=True referencing this factor.
    Property 7 implementation.
    """
    from apps.environmental.models import CarbonEmission
    affected = CarbonEmission.objects.filter(
        emission_factor=instance,
        auto_recalculate=True
    )
    for emission in affected:
        emission.co2e_value = emission.activity_value * instance.coefficient
        emission.save(update_fields=['co2e_value', 'updated_at'])
```

### Overdue detection — management command

```python
# governance/management/commands/check_overdue.py
# Run daily via cron: python manage.py check_overdue

class Command(BaseCommand):
    def handle(self, *args, **options):
        today = date.today()
        # Sustainability Goals
        SustainabilityGoal.objects.filter(
            deadline__lt=today, status='active'
        ).exclude(current_value__gte=F('target_value')).update(status='overdue')

        SustainabilityGoal.objects.filter(
            current_value__gte=F('target_value')
        ).update(status='completed')

        # Compliance Issues
        overdue_issues = ComplianceIssue.objects.filter(
            due_date__lt=today, is_overdue=False
        ).exclude(status='resolved')
        for issue in overdue_issues:
            issue.is_overdue = True
            issue.save()
            NotificationService.send(
                recipients=[issue.owner],
                event_type=NotificationEvent.COMPLIANCE_OVERDUE,
                title=f'Compliance Issue Overdue: {issue.title}',
                message=f'Issue "{issue.title}" is past its due date.',
            )
```

---

## Notification Delivery System

### NotificationService

```python
# notifications/services.py

from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, NotificationPreference, PlatformNotificationConfig, NotificationEvent


class NotificationService:

    @staticmethod
    def send(recipients, event_type: str, title: str, message: str, reference_id: int = None):
        """
        Create in-app notifications and optionally send email for each recipient.
        Respects platform-level config AND per-user preferences.
        """
        platform_cfg = PlatformNotificationConfig.objects.filter(event_type=event_type).first()
        platform_email_on = platform_cfg.email_enabled if platform_cfg else True

        for user in recipients:
            # Create in-app notification always
            notif = Notification.objects.create(
                recipient=user,
                event_type=event_type,
                title=title,
                message=message,
            )

            # Email delivery: platform level AND user preference must both be enabled
            if platform_email_on:
                user_pref = NotificationPreference.objects.filter(
                    user=user, event_type=event_type
                ).first()
                user_email_on = user_pref.email_enabled if user_pref else True

                if user_email_on and user.email:
                    send_mail(
                        subject=title,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
```

### Unread count via context processor

```python
# notifications/context_processors.py

def unread_notifications(request):
    if request.user.is_authenticated:
        return {'unread_count': request.user.notifications.filter(is_read=False).count()}
    return {'unread_count': 0}
```

Add to `TEMPLATES[0]['OPTIONS']['context_processors']` in `settings.py`.

---

## Report Generation and Export Pipeline

### Report service pattern

All report types share the same interface:

```python
# reports/services.py

import csv
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from openpyxl import Workbook


class ReportService:

    @staticmethod
    def build_environmental(date_from, date_to, departments):
        """Returns dict: { 'rows': [...], 'summary': {...} }"""
        from apps.environmental.models import CarbonEmission, SustainabilityGoal
        emissions = CarbonEmission.objects.filter(
            department__in=departments,
            reporting_period__range=(date_from, date_to)
        ).select_related('department', 'emission_factor')
        goals = SustainabilityGoal.objects.filter(
            department__in=departments
        )
        rows = [
            {
                'department': e.department.name,
                'source': e.emission_source,
                'co2e': float(e.co2e_value),
                'period': str(e.reporting_period),
                'factor': e.emission_factor.name,
            }
            for e in emissions
        ]
        return {'rows': rows, 'goals': [
            {'title': g.title, 'progress': g.progress_percentage, 'status': g.status}
            for g in goals
        ]}

    @staticmethod
    def export_csv(headers, rows) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode('utf-8')

    @staticmethod
    def export_excel(headers, rows) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, '') for h in headers])
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_pdf(title, headers, rows) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        data = [headers] + [[row.get(h, '') for h in headers] for row in rows]
        table = Table(data)
        doc.build([Paragraph(title), table])
        return buffer.getvalue()
```

### Custom Report Builder flow

1. User submits `CustomReportForm` (modules, date range, departments).
2. View calls `ReportService.build_*()` for each selected module and merges results.
3. `CustomReportAudit` record is saved with parameters and timestamp.
4. Response streams the selected format as a file download (`Content-Disposition: attachment`).

```python
# reports/models.py

class CustomReportAudit(models.Model):
    generated_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    modules        = models.JSONField()          # list of selected module names
    date_from      = models.DateField()
    date_to        = models.DateField()
    departments    = models.ManyToManyField('core.Department')
    export_format  = models.CharField(max_length=10)  # pdf, excel, csv
    generated_at   = models.DateTimeField(auto_now_add=True)
```

---

## Gamification Engine

### GamificationService

```python
# gamification/services.py

from django.db import transaction
from django.utils import timezone
from .models import XPLedger, Badge, BadgeAward, Reward, RedemptionTransaction


class GamificationService:

    @staticmethod
    @transaction.atomic
    def award_xp(employee, amount: int, source: str, reference_id: int = None, note: str = ''):
        """Add XP to employee's balance and write ledger entry."""
        profile = employee.profile
        # Get last balance from ledger
        last_entry = XPLedger.objects.filter(employee=employee).order_by('-timestamp').first()
        current_balance = last_entry.balance_after if last_entry else 0
        new_balance = current_balance + amount

        XPLedger.objects.create(
            employee=employee,
            source=source,
            reference_id=reference_id,
            amount=amount,
            balance_after=new_balance,
            note=note,
        )
        return new_balance

    @staticmethod
    def get_xp_balance(employee) -> int:
        entry = XPLedger.objects.filter(employee=employee).order_by('-timestamp').first()
        return entry.balance_after if entry else 0

    @staticmethod
    @transaction.atomic
    def redeem_reward(employee, reward: Reward):
        """
        Attempt reward redemption.
        Returns (success: bool, message: str).
        """
        balance = GamificationService.get_xp_balance(employee)
        if balance < reward.xp_cost:
            return False, 'Insufficient XP balance.'
        if reward.stock_quantity <= 0:
            return False, 'Reward is out of stock.'

        # Deduct XP
        GamificationService.award_xp(
            employee=employee,
            amount=-reward.xp_cost,
            source='redemption',
            reference_id=reward.id,
            note=f'Redeemed: {reward.name}',
        )

        # Decrement stock
        reward.stock_quantity -= 1
        if reward.stock_quantity == 0:
            reward.is_out_of_stock = True
        reward.save()

        # Record transaction
        RedemptionTransaction.objects.create(
            employee=employee,
            reward=reward,
            xp_spent=reward.xp_cost,
        )
        return True, 'Redemption successful.'

    @staticmethod
    def evaluate_badges_for(employee):
        """
        Evaluate all auto-award badges against the employee's current stats.
        Award any not yet awarded badges whose criteria are met.
        """
        from notifications.services import NotificationService
        from notifications.models import NotificationEvent

        balance = GamificationService.get_xp_balance(employee)
        challenges_completed = XPLedger.objects.filter(employee=employee, source='challenge').count()

        for badge in Badge.objects.filter(auto_award=True):
            if BadgeAward.objects.filter(badge=badge, employee=employee).exists():
                continue  # already awarded

            criteria_met = False
            if badge.criteria_type == 'xp_threshold':
                criteria_met = balance >= badge.criteria_value
            elif badge.criteria_type == 'challenges_completed':
                criteria_met = challenges_completed >= badge.criteria_value
            elif badge.criteria_type == 'category_participation':
                if badge.criteria_category:
                    from apps.gamification.models import ChallengeEnrolment
                    count = ChallengeEnrolment.objects.filter(
                        employee=employee,
                        challenge__category=badge.criteria_category,
                        challenge__status='completed'
                    ).count()
                    criteria_met = count >= badge.criteria_value

            if criteria_met:
                BadgeAward.objects.create(badge=badge, employee=employee, awarded_by=None)
                NotificationService.send(
                    recipients=[employee],
                    event_type=NotificationEvent.BADGE_UNLOCKED,
                    title=f'Badge Unlocked: {badge.name}',
                    message=f'You have earned the "{badge.name}" badge!',
                )
```

### Challenge Lifecycle State Machine

```
Draft ──[ESG Manager activates]──► Active ──[end_date passes]──► Under Review
                                                                       │
                                    ┌──────────────────────────────────┤
                                    ▼                                  ▼
                                Completed                          Archived
```

Transitions are enforced in the `ChallengeService`:

```python
VALID_TRANSITIONS = {
    'draft':        ['active'],
    'active':       ['under_review', 'archived'],
    'under_review': ['completed', 'archived'],
    'completed':    [],
    'archived':     [],
}

def transition_challenge(challenge, new_status, actor):
    if new_status not in VALID_TRANSITIONS[challenge.status]:
        raise ValueError(f"Invalid transition: {challenge.status} → {new_status}")
    challenge.status = new_status
    challenge.save()
    # Notify enrolled employees on status change
    ...
```

### Leaderboard query

```python
# gamification/services.py

def get_employee_leaderboard(limit=10):
    from django.db.models import Max
    return (
        XPLedger.objects
        .values('employee')
        .annotate(total_xp=Max('balance_after'))
        .order_by('-total_xp')[:limit]
    )

def get_department_leaderboard(limit=10):
    from apps.dashboard.models import DepartmentESGScore
    return DepartmentESGScore.objects.select_related('department').order_by('-overall_score')[:limit]
```

---

## Chart.js Integration

All Chart.js charts follow this pattern: the Django view passes serialised data as JSON into the template context, and a small `<script>` block in each template (or a shared `chart_init.js`) initialises the chart.

### Data serialisation in views

```python
# dashboard/views.py

import json
from django.core.serializers.json import DjangoJSONEncoder

class MainDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/main.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dept_scores = DepartmentESGScore.objects.select_related('department').order_by('-overall_score')
        ctx['chart_data'] = json.dumps({
            'labels': [d.department.name for d in dept_scores],
            'env':    [float(d.environmental_score) for d in dept_scores],
            'social': [float(d.social_score) for d in dept_scores],
            'gov':    [float(d.governance_score) for d in dept_scores],
            'overall':[float(d.overall_score) for d in dept_scores],
        }, cls=DjangoJSONEncoder)
        return ctx
```

### Template chart block

```html
<!-- templates/partials/chart_card.html -->
<div class="bg-white rounded-xl shadow p-4 w-full">
  <canvas id="{{ chart_id }}" class="w-full"></canvas>
</div>

{% block scripts %}
<script>
  const data = {{ chart_data|safe }};
  new Chart(document.getElementById('esgBarChart'), {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [
        { label: 'Environmental', data: data.env,    backgroundColor: '#22c55e' },
        { label: 'Social',        data: data.social, backgroundColor: '#3b82f6' },
        { label: 'Governance',    data: data.gov,    backgroundColor: '#a855f7' },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { min: 0, max: 100 } }
    }
  });
</script>
{% endblock %}
```

### Chart inventory

| Dashboard         | Chart type        | Data source                              |
|-------------------|-------------------|------------------------------------------|
| Main dashboard    | Grouped bar       | DepartmentESGScore (all components)      |
| Main dashboard    | Doughnut          | Org-level ESG component proportions      |
| Environmental     | Line (time-series)| CarbonEmission grouped by period         |
| Environmental     | Horizontal bar    | Dept CO2e ranking                        |
| Environmental     | Progress bars     | SustainabilityGoal progress_percentage   |
| Social dashboard  | Bar               | CSR participation rates per dept         |
| Social dashboard  | Pie               | Diversity metric breakdown               |
| Governance dash   | Doughnut          | Audit completion ratio                   |
| Gamification      | Bar               | XP leaderboard top 10                    |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Role-based access denial

*For any* protected view that requires a specific role and any authenticated user whose assigned role is not in the view's allowed role set, the platform SHALL deny access (HTTP 403 or redirect to login).

**Validates: Requirements 1.3**

---

### Property 2: Unauthenticated redirect to login

*For any* URL marked as login-required, an unauthenticated HTTP request SHALL receive a redirect response pointing to the login page, regardless of the URL being requested.

**Validates: Requirements 1.6**

---

### Property 3: Single department membership invariant

*For any* user in the system, the count of department associations for that user SHALL be at most one (UserProfile.department is a single nullable FK).

**Validates: Requirements 1.4**

---

### Property 4: ESG weight validation

*For any* three numeric values submitted as Environmental, Social, and Governance weights, the ESG Configuration form SHALL accept the submission if and only if the three values sum to exactly 100; all other combinations SHALL be rejected with a validation error.

**Validates: Requirements 4.3, 4.4**

---

### Property 5: Weight update triggers full recalculation

*For any* set of departments that have an existing ESG Score snapshot, saving a new valid ESGConfiguration SHALL result in a recalculated `overall_score` for every active department, using the newly stored weights.

**Validates: Requirements 4.5**

---

### Property 6: Carbon emission CO₂e calculation

*For any* positive activity value `a` and any active Emission Factor with coefficient `c`, saving a CarbonEmission record with those values SHALL produce a stored `co2e_value` equal to `a × c` (within decimal precision).

**Validates: Requirements 6.2**

---

### Property 7: Auto-recalculation on factor coefficient change

*For any* CarbonEmission record with `auto_recalculate=True` and any update to the coefficient of its referenced EmissionFactor, the record's `co2e_value` SHALL be updated to `activity_value × new_coefficient`. Implemented via the `on_emission_factor_change` signal receiver in `dashboard/signals.py`.

**Validates: Requirements 6.3, 6.4**

---

### Property 8: Sustainability goal progress percentage

*For any* SustainabilityGoal with a positive `target_value`, the computed `progress_percentage` SHALL equal `(current_value / target_value) × 100`, capped at 100.

**Validates: Requirements 7.3**

---

### Property 9: Sustainability goal status transitions

*For any* SustainabilityGoal, after the daily status check runs:
- If `current_value >= target_value`, status SHALL be `completed`.
- Else if `deadline < today` and status is not `completed`, status SHALL be `overdue`.

**Validates: Requirements 7.4, 7.5**

---

### Property 10: CSR enrolment capacity enforcement

*For any* CSRActivity whose current enrolment count equals `max_participants`, any additional enrolment attempt SHALL be rejected and the enrolment count SHALL remain unchanged.

**Validates: Requirements 9.9**

---

### Property 11: XP award correctness

*For any* employee and any positive XP amount `x` awarded via challenge approval or CSR approval, the employee's XP balance after the award SHALL equal the balance before the award plus `x`, and a corresponding `XPLedger` entry SHALL exist with `amount = x`, the correct `source`, and the correct `balance_after`.

**Validates: Requirements 16.1, 16.2, 16.3**

---

### Property 12: Reward redemption gate

*For any* redemption attempt by an employee with XP balance `b` against a Reward with cost `c` and stock `s`:
- The redemption SHALL succeed if and only if `b >= c` AND `s > 0`.
- On success, the employee's balance SHALL decrease by exactly `c`, the reward's stock SHALL decrease by exactly 1, and a `RedemptionTransaction` SHALL be recorded.
- On failure, balance and stock SHALL remain unchanged.

**Validates: Requirements 18.3, 18.4, 18.5**

---

### Property 13: ESG score is a bounded weighted sum

*For any* department with component scores `e`, `s`, `g` each in [0, 100] and active weights `we`, `ws`, `wg` summing to 100, the computed `overall_score` SHALL equal `(e×we + s×ws + g×wg) / 100`, and SHALL always lie within [0, 100].

**Validates: Requirements 20.1, 20.3**

---

### Property 14: Notification unread count accuracy

*For any* user, the unread notification count displayed in the navigation SHALL equal the exact count of `Notification` records for that user where `is_read=False`.

**Validates: Requirements 27.3**

---

### Property 15: Notification read state transition

*For any* unread `Notification` record belonging to a user, after the user views that notification, the record's `is_read` field SHALL be `True` and the unread count SHALL decrease by exactly one.

**Validates: Requirements 27.4**

---

### Property 16: Notification email preference enforcement

*For any* user who has disabled email notifications for event type `E`, and any `Notification` of type `E` created for that user, no email SHALL be sent to that user, while the in-app `Notification` record SHALL still be created.

**Validates: Requirements 27.7, 28.2**
