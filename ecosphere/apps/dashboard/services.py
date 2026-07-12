from decimal import Decimal
from apps.core.models import ESGConfiguration

def calculate_environmental_score(department) -> Decimal:
    """
    Score based on CO2e reduction progress against Sustainability Goals.
    Normalised to 0-100: average progress_percentage across active/completed goals.
    If no goals exist, score = 50 (neutral baseline).
    """
    from apps.environmental.models import SustainabilityGoal
    goals = SustainabilityGoal.objects.filter(
        department=department, status__in=['active', 'completed']
    )
    if not goals.exists():
        return Decimal('50.00')
    total_progress = sum(Decimal(str(g.progress_percentage)) for g in goals)
    return Decimal(str(min(total_progress / goals.count(), 100))).quantize(Decimal('0.01'))


def calculate_social_score(department) -> Decimal:
    """
    Weighted average of:
      - CSR participation rate (40%)
      - Training completion rate (40%)
      - Diversity metric presence score (20%)
    """
    from apps.social.models import CSRActivity, CSRParticipation, TrainingCompletion, Training, DiversityMetric

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
    return Decimal(str(min(max(score, 0), 100))).quantize(Decimal('0.01'))


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
    return Decimal(str(min(max(score, 0), 100))).quantize(Decimal('0.01'))


def recalculate_department_esg(department):
    """
    Recalculate and persist ESG scores for a single department.
    Called by Django signals whenever underlying data changes.
    """
    from apps.dashboard.models import DepartmentESGScore
    config = ESGConfiguration.get_config()

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
            'overall_score': Decimal(str(round(overall, 2))),
        }
    )


def recalculate_all_departments():
    """Triggered when ESGConfiguration weights change."""
    from apps.core.models import Department
    for dept in Department.objects.filter(is_active=True):
        recalculate_department_esg(dept)
