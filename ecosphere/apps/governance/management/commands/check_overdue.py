from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.environmental.models import SustainabilityGoal
from apps.governance.models import ComplianceIssue
from apps.notifications.services import NotificationService
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Flag overdue sustainability goals and compliance issues, sending in-app alerts."

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write("Running overdue checker...")

        # 1. Sustainability Goals
        active_goals = SustainabilityGoal.objects.filter(status='active')
        for goal in active_goals:
            # Check completion first
            if goal.current_value >= goal.target_value:
                goal.status = 'completed'
                goal.save()
                self.stdout.write(f"Goal '{goal.title}' marked as COMPLETED.")
                
                # Notify managers
                managers = User.objects.filter(profile__role__in=['super_admin', 'esg_manager'])
                NotificationService.send(
                    recipients=managers,
                    event_type='GOAL_STATUS',
                    title=f"Goal Completed: {goal.title}",
                    message=f"The goal '{goal.title}' has been successfully completed ahead of schedule!"
                )
            # Check overdue
            elif goal.deadline < today:
                goal.status = 'overdue'
                goal.save()
                self.stdout.write(f"Goal '{goal.title}' marked as OVERDUE.")
                
                # Notify managers
                managers = User.objects.filter(profile__role__in=['super_admin', 'esg_manager'])
                NotificationService.send(
                    recipients=managers,
                    event_type='GOAL_STATUS',
                    title=f"Goal Overdue: {goal.title}",
                    message=f"The deadline for goal '{goal.title}' was {goal.deadline} and was not met."
                )

        # 2. Compliance Issues
        open_issues = ComplianceIssue.objects.filter(status='open', is_overdue=False)
        for issue in open_issues:
            if issue.due_date < today:
                issue.is_overdue = True
                issue.save()
                self.stdout.write(f"Compliance issue '{issue.title}' flagged as OVERDUE.")

                # Notify owner
                NotificationService.send(
                    recipients=issue.owner,
                    event_type='COMPLIANCE_OVERDUE',
                    title=f"Compliance Issue OVERDUE: {issue.title}",
                    message=f"The compliance issue '{issue.title}' assigned to you is overdue. Deadline was {issue.due_date}."
                )
                
        self.stdout.write("Overdue checker run complete.")
