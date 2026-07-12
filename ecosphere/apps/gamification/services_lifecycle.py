from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Challenge, ChallengeEnrolment
from .services import GamificationService
from apps.notifications.services import NotificationService

class ChallengeService:
    VALID_TRANSITIONS = {
        'draft': ['active', 'archived'],
        'active': ['under_review', 'archived'],
        'under_review': ['completed'],
        'completed': [],
        'archived': []
    }

    @classmethod
    @transaction.atomic
    def transition_challenge(cls, challenge, new_status, actor=None):
        old_status = challenge.status
        if old_status == new_status:
            return

        allowed = cls.VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from '{old_status}' to '{new_status}'.")

        challenge.status = new_status
        challenge.save()

        # Lifecycle logic triggers
        if new_status == 'active':
            # Send notifications to eligible employees
            if challenge.target_all:
                recipients = User.objects.filter(profile__role='employee')
            else:
                recipients = User.objects.filter(profile__role='employee', profile__department__in=challenge.departments.all())
            
            NotificationService.send(
                recipients=recipients,
                event_type='CHALLENGE_STATUS',
                title=f"New Challenge Active: {challenge.title}",
                message=f"A new challenge '{challenge.title}' has started! Enroll now to earn {challenge.xp_reward} XP."
            )

        elif new_status == 'completed':
            # Award XP to all enrolled employees
            enrolments = ChallengeEnrolment.objects.filter(challenge=challenge)
            for enrol in enrolments:
                # Award XP
                if challenge.xp_reward > 0:
                    GamificationService.award_xp(
                        employee=enrol.employee,
                        amount=challenge.xp_reward,
                        source='challenge',
                        reference_id=challenge.pk,
                        note=f"Completed challenge: {challenge.title}"
                    )
                # Send completion notification
                NotificationService.send(
                    recipients=enrol.employee,
                    event_type='CHALLENGE_STATUS',
                    title=f"Challenge Completed: {challenge.title}",
                    message=f"Congratulations! You completed '{challenge.title}' and earned {challenge.xp_reward} XP."
                )
