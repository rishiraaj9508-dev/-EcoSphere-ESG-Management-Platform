from .models import Badge, BadgeAward, ChallengeEnrolment
from .services import GamificationService

def evaluate_badges_for(employee):
    # Fetch all auto-award badges
    badges = Badge.objects.filter(auto_award=True)
    
    # Fetch employee's current XP balance
    xp_balance = GamificationService.get_xp_balance(employee)
    
    # Fetch employee's completed challenges count
    completed_enrolments = ChallengeEnrolment.objects.filter(
        employee=employee,
        challenge__status='completed'
    )
    challenges_completed_count = completed_enrolments.count()
    
    for badge in badges:
        # Check if already awarded
        if BadgeAward.objects.filter(badge=badge, employee=employee).exists():
            continue
            
        is_eligible = False
        
        if badge.criteria_type == 'xp_threshold':
            if xp_balance >= badge.criteria_value:
                is_eligible = True
                
        elif badge.criteria_type == 'challenges_completed':
            if challenges_completed_count >= badge.criteria_value:
                is_eligible = True
                
        elif badge.criteria_type == 'category_participation':
            # Count completed challenges in specific category
            cat_count = completed_enrolments.filter(
                challenge__category=badge.criteria_category
            ).count()
            if cat_count >= badge.criteria_value:
                is_eligible = True
                
        if is_eligible:
            # Award the badge!
            BadgeAward.objects.create(
                badge=badge,
                employee=employee
            )
