from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.gamification.models import Challenge
from apps.gamification.services_lifecycle import ChallengeService

class Command(BaseCommand):
    help = "Flag active challenges past their end date to under_review."

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write("Running challenge status updater...")

        active_challenges = Challenge.objects.filter(status='active')
        for ch in active_challenges:
            if ch.end_date < today:
                try:
                    ChallengeService.transition_challenge(ch, 'under_review')
                    self.stdout.write(f"Challenge '{ch.title}' transitioned to UNDER REVIEW.")
                except ValueError as e:
                    self.stdout.write(f"Failed to transition challenge '{ch.title}': {str(e)}")
                    
        self.stdout.write("Challenge status updater complete.")
