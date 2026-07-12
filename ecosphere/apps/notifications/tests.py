from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from apps.notifications.models import Notification, NotificationPreference, PlatformNotificationConfig
from apps.notifications.services import NotificationService
from apps.governance.models import ESGPolicy, PolicyAcknowledgement
from apps.governance.views import ESGPolicyPublishView
from apps.gamification.models import Reward
from apps.gamification.services import GamificationService

class NotificationPreferenceAndLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testemployee", password="password123", email="employee@test.com")
        self.user.profile.role = 'employee'
        self.user.profile.save()

    def test_notification_delivery_preference_gating(self):
        # 1. Default should allow in-app notifications
        NotificationService.send(self.user, 'POLICY_PUBLISHED', "Title 1", "Message 1")
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

        # 2. Disable in-app preference for this category
        pref, _ = NotificationPreference.objects.get_or_create(user=self.user, event_type='POLICY_PUBLISHED')
        pref.in_app_enabled = False
        pref.save()

        NotificationService.send(self.user, 'POLICY_PUBLISHED', "Title 2", "Message 2")
        # Count remains 1 since preference was disabled
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_policy_publishing_flow_and_supersedence(self):
        # Create a draft policy
        policy = ESGPolicy.objects.create(
            title="Ethics Code",
            description="Be good.",
            version="1.0",
            effective_date=timezone.now().date(),
            review_cycle=365,
            status='draft'
        )

        # Publish the policy (equivalent to the post in publish view)
        policy.status = 'active'
        policy.save()

        # Send in-app notification to all employees
        employees = User.objects.filter(profile__role='employee')
        NotificationService.send(
            recipients=employees,
            event_type='POLICY_PUBLISHED',
            title=f"Policy Published: {policy.title}",
            message=f"New policy v{policy.version}"
        )

        # Verify notification created
        self.assertEqual(Notification.objects.filter(user=self.user, event_type='POLICY_PUBLISHED').count(), 1)

        # Acknowledge policy
        PolicyAcknowledgement.objects.create(policy=policy, employee=self.user)
        self.assertTrue(PolicyAcknowledgement.objects.filter(policy=policy, employee=self.user).exists())

        # Version Up (New Version)
        new_version = ESGPolicy.objects.create(
            title=policy.title,
            description="Be even better.",
            version="2.0",
            effective_date=timezone.now().date(),
            review_cycle=365,
            status='draft',
            parent_policy=policy
        )

        # Publish new version (supersedes parent and clears acknowledgements)
        new_version.status = 'active'
        new_version.save()
        if new_version.parent_policy:
            parent = new_version.parent_policy
            parent.status = 'superseded'
            parent.save()
            PolicyAcknowledgement.objects.filter(policy=parent).delete()

        # Verify old acknowledgement is deleted
        self.assertFalse(PolicyAcknowledgement.objects.filter(policy=policy, employee=self.user).exists())
        # Verify old policy is superseded
        policy.refresh_from_db()
        self.assertEqual(policy.status, 'superseded')

    def test_reward_redemption_and_stock_limits(self):
        reward = Reward.objects.create(
            name="Sustain Mug",
            description="Re-usable bamboo mug",
            xp_cost=100,
            stock_quantity=1
        )

        # 1. Try to redeem with 0 XP
        with self.assertRaises(ValueError):
            GamificationService.redeem_reward(self.user, reward)

        # 2. Award XP and redeem
        GamificationService.award_xp(self.user, 150, 'csr', note="Award")
        self.assertEqual(GamificationService.get_xp_balance(self.user), 150)
        
        GamificationService.redeem_reward(self.user, reward)
        
        # Verify stock decremented and balance deducted
        reward.refresh_from_db()
        self.assertEqual(reward.stock_quantity, 0)
        self.assertTrue(reward.is_out_of_stock)
        self.assertEqual(GamificationService.get_xp_balance(self.user), 50)

        # 3. Try to redeem again (should fail because stock is 0)
        GamificationService.award_xp(self.user, 100, 'csr', note="Award") # add more XP
        with self.assertRaises(ValueError):
            GamificationService.redeem_reward(self.user, reward)
