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
    dept = instance.department
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=CSRParticipation)
def on_social_csr_change(sender, instance, **kwargs):
    dept = instance.activity.department
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=TrainingCompletion)
def on_social_training_change(sender, instance, **kwargs):
    dept = instance.training.department
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=PolicyAcknowledgement)
def on_policy_ack_change(sender, instance, **kwargs):
    if hasattr(instance.employee, 'profile') and instance.employee.profile.department:
        recalculate_department_esg(instance.employee.profile.department)

@receiver(post_save, sender=Audit)
def on_audit_change(sender, instance, **kwargs):
    dept = instance.department
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=ComplianceIssue)
def on_compliance_issue_change(sender, instance, **kwargs):
    dept = instance.department
    if dept:
        recalculate_department_esg(dept)

@receiver(post_save, sender=ESGConfiguration)
def on_config_change(sender, instance, **kwargs):
    recalculate_all_departments()

@receiver(post_save, sender=EmissionFactor)
def on_emission_factor_change(sender, instance, **kwargs):
    """
    Cascade CO2e updates to all CarbonEmissions with auto_recalculate=True
    referencing this EmissionFactor. Property 7 implementation.
    """
    affected_emissions = CarbonEmission.objects.filter(
        emission_factor=instance,
        auto_recalculate=True
    )
    for emission in affected_emissions:
        # Saving will automatically trigger the on_env_data_change signal
        # which will trigger recalculate_department_esg
        emission.save()
