from django.db import models
from django.conf import settings

class CSRActivity(models.Model):
    STATUS_CHOICES = [('upcoming','Upcoming'),('active','Active'),('closed','Closed')]

    title             = models.CharField(max_length=200)
    description       = models.TextField()
    category          = models.ForeignKey('core.Category', on_delete=models.SET_NULL, null=True, blank=True)
    department        = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    start_date        = models.DateField()
    end_date          = models.DateField()
    max_participants  = models.PositiveIntegerField()
    requires_evidence = models.BooleanField(default=False)
    xp_reward         = models.PositiveIntegerField(default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "CSR Activity"
        verbose_name_plural = "CSR Activities"

    def __str__(self):
        return self.title


class CSRParticipation(models.Model):
    STATUS_CHOICES = [('enrolled','Enrolled'),('pending_review','Pending Review'),('approved','Approved'),('rejected','Rejected')]

    activity     = models.ForeignKey(CSRActivity, on_delete=models.CASCADE, related_name='participations')
    employee     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evidence_url = models.URLField(blank=True)
    evidence_file= models.FileField(upload_to='csr_evidence/', blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    reviewed_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_participations')

    class Meta:
        unique_together = ('activity', 'employee')

    def __str__(self):
        return f"{self.employee.username} - {self.activity.title} ({self.status})"


class DiversityMetric(models.Model):
    department       = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    metric_type      = models.CharField(max_length=100)  # gender_ratio, age_group, etc.
    value            = models.DecimalField(max_digits=10, decimal_places=4)
    unit             = models.CharField(max_length=50)
    reporting_period = models.DateField()
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.metric_type} - {self.department.name} ({self.reporting_period})"


class Training(models.Model):
    title         = models.CharField(max_length=200)
    department    = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    training_date = models.DateField()
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TrainingCompletion(models.Model):
    training  = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='completions')
    employee  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('training', 'employee')

    def __str__(self):
        return f"{self.employee.username} - {self.training.title} ({self.completed})"
