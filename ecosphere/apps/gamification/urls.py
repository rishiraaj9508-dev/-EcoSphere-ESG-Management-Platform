from django.urls import path
from .views import (
    ChallengeListView, ChallengeCreateView, ChallengeEnrolView, ChallengeSubmitEvidenceView,
    ChallengeTransitionView, BadgeListView, BadgeCreateView, RewardListView, RewardCreateView,
    RewardRedeemView, LeaderboardView
)

app_name = 'gamification'

urlpatterns = [
    # Challenges
    path('challenges/', ChallengeListView.as_view(), name='challenges'),
    path('challenges/add/', ChallengeCreateView.as_view(), name='challenge-add'),
    path('challenges/<int:pk>/enrol/', ChallengeEnrolView.as_view(), name='enrol'),
    path('challenges/enrolment/<int:pk>/submit/', ChallengeSubmitEvidenceView.as_view(), name='submit'),
    path('challenges/<int:pk>/transition/', ChallengeTransitionView.as_view(), name='challenge-transition'),
    
    # Badges
    path('badges/', BadgeListView.as_view(), name='badges'),
    path('badges/add/', BadgeCreateView.as_view(), name='badge-add'),
    
    # Rewards
    path('rewards/', RewardListView.as_view(), name='rewards'),
    path('rewards/add/', RewardCreateView.as_view(), name='reward-add'),
    path('rewards/<int:pk>/redeem/', RewardRedeemView.as_view(), name='redeem'),
    
    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
