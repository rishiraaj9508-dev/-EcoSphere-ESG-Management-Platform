from django.db import models
from django.conf import settings

class Challenge(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('active','Active'),('under_review','Under Review'),('completed','Completed'),('archived','Archived')]

    title          = models.CharField(max_length=200)
    description    = models.TextField()
    category       = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True, blank=True)
    xp_reward      = models.PositiveIntegerField()
    start_date     = models.DateField()
    end_date       = models.DateField()
    target_all     = models.BooleanField(default=True)  # True = all employees
    departments    = models.ManyToManyField('core.Department', blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ChallengeEnrolment(models.Model):
    challenge        = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='enrolments')
    employee         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evidence_url     = models.URLField(blank=True)
    evidence_file    = models.FileField(upload_to='challenge_evidence/', blank=True)
    submitted_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('challenge', 'employee')

    def __str__(self):
        return f"{self.employee.username} - {self.challenge.title}"


class XPLedger(models.Model):
    SOURCE_CHOICES = [('challenge','Challenge'),('csr','CSR Activity'),('badge','Badge'),('admin','Admin Award'),('redemption','Redemption')]

    employee  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_ledger')
    source    = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    reference_id = models.PositiveIntegerField(null=True, blank=True)  # ID of source object
    amount    = models.IntegerField()  # positive = earn, negative = spend
    balance_after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    note      = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.employee.username} - {self.amount} ({self.source})"


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

    def __str__(self):
        return self.name


class BadgeAward(models.Model):
    badge       = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    employee    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    awarded_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_badges')
    awarded_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('badge', 'employee')

    def __str__(self):
        return f"{self.employee.username} - {self.badge.name}"


class Reward(models.Model):
    name           = models.CharField(max_length=200)
    description    = models.TextField()
    xp_cost        = models.PositiveIntegerField()
    stock_quantity = models.IntegerField(default=0)
    is_out_of_stock= models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RedemptionTransaction(models.Model):
    employee   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reward     = models.ForeignKey(Reward, on_delete=models.PROTECT)
    xp_spent   = models.PositiveIntegerField()
    redeemed_at= models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.username} redeemed {self.reward.name}"
