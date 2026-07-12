from django.db import transaction
from .models import XPLedger, Reward, RedemptionTransaction

class GamificationService:
    @staticmethod
    def get_xp_balance(employee):
        last_entry = XPLedger.objects.filter(employee=employee).order_by('-timestamp', '-id').first()
        if last_entry:
            return last_entry.balance_after
        return 0

    @staticmethod
    @transaction.atomic
    def award_xp(employee, amount, source, reference_id=None, note=""):
        if amount == 0:
            return None
            
        current_balance = GamificationService.get_xp_balance(employee)
        new_balance = current_balance + amount
        
        ledger_entry = XPLedger.objects.create(
            employee=employee,
            source=source,
            reference_id=reference_id,
            amount=amount,
            balance_after=new_balance,
            note=note
        )
        
        # Trigger badge evaluation (Task 7.8)
        try:
            from apps.gamification.services_badge import evaluate_badges_for
            evaluate_badges_for(employee)
        except ImportError:
            pass
            
        return ledger_entry

    @staticmethod
    @transaction.atomic
    def redeem_reward(employee, reward):
        if reward.stock_quantity <= 0:
            raise ValueError("This reward is out of stock.")
            
        current_balance = GamificationService.get_xp_balance(employee)
        if current_balance < reward.xp_cost:
            raise ValueError("Insufficient XP balance to redeem this reward.")
            
        # Deduct XP (award negative amount)
        GamificationService.award_xp(
            employee=employee,
            amount=-reward.xp_cost,
            source='redemption',
            note=f"Redeemed reward: {reward.name}"
        )
        
        # Decrement stock
        reward.stock_quantity -= 1
        if reward.stock_quantity == 0:
            reward.is_out_of_stock = True
        reward.save()
        
        # Create transaction record
        tx = RedemptionTransaction.objects.create(
            employee=employee,
            reward=reward,
            xp_spent=reward.xp_cost
        )
        return tx
