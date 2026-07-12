from django.db import models
from django.conf import settings

class ESGPolicy(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('active','Active'),('superseded','Superseded')]

    title          = models.CharField(max_length=200)
    description    = models.TextField()
    category       = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True, blank=True)
    version        = models.CharField(max_length=20)
    effective_date = models.DateField()
    review_cycle   = models.PositiveIntegerField(help_text='Review cycle in days')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    parent_policy  = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='versions')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ESG Policy"
        verbose_name_plural = "ESG Policies"

    def __str__(self):
        return f"{self.title} (v{self.version})"


class PolicyAcknowledgement(models.Model):
    policy       = models.ForeignKey(ESGPolicy, on_delete=models.CASCADE, related_name='acknowledgements')
    employee     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('policy', 'employee')

    def __str__(self):
        return f"{self.employee.username} - {self.policy.title}"


class Audit(models.Model):
    STATUS_CHOICES = [('planned','Planned'),('in_progress','In Progress'),('completed','Completed')]

    title           = models.CharField(max_length=200)
    department      = models.ForeignKey('core.Department', on_delete=models.PROTECT, related_name='audits')
    scope           = models.TextField()
    auditor         = models.CharField(max_length=200)
    audit_date      = models.DateField()
    findings        = models.TextField(blank=True)
    resolution_notes= models.TextField(blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ComplianceIssue(models.Model):
    SEVERITY_CHOICES = [('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')]
    STATUS_CHOICES   = [('open','Open'),('in_progress','In Progress'),('resolved','Resolved')]

    title         = models.CharField(max_length=200)
    description   = models.TextField()
    department    = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    owner         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_issues')
    due_date      = models.DateField()
    severity      = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_overdue    = models.BooleanField(default=False)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
