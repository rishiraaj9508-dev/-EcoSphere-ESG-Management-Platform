from django.db import models
from django.core.exceptions import ValidationError

class EmissionFactor(models.Model):
    name        = models.CharField(max_length=150)
    unit        = models.CharField(max_length=50)  # e.g. kWh, km, litre
    coefficient = models.DecimalField(max_digits=12, decimal_places=6)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(coefficient__gt=0), name='emission_factor_positive')
        ]

    def __str__(self):
        return f"{self.name} ({self.coefficient} CO2e/{self.unit})"


class CarbonEmission(models.Model):
    department       = models.ForeignKey('core.Department', on_delete=models.PROTECT, related_name='emissions')
    emission_source  = models.CharField(max_length=200)
    activity_value   = models.DecimalField(max_digits=14, decimal_places=4)
    emission_factor  = models.ForeignKey(EmissionFactor, on_delete=models.PROTECT, related_name='emissions')
    co2e_value       = models.DecimalField(max_digits=14, decimal_places=4, editable=False)
    auto_recalculate = models.BooleanField(default=True)
    reporting_period = models.DateField()  # convention: YYYY-MM-01
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Calculate co2e_value as activity_value * coefficient
        self.co2e_value = self.activity_value * self.emission_factor.coefficient
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.emission_source} - {self.department.name} ({self.reporting_period})"


class SustainabilityGoal(models.Model):
    STATUS_CHOICES = [('active','Active'),('overdue','Overdue'),('completed','Completed')]
    SCOPE_CHOICES  = [('org','Organization-wide'),('dept','Department-specific')]

    title          = models.CharField(max_length=200)
    target_metric  = models.CharField(max_length=150)
    target_value   = models.DecimalField(max_digits=14, decimal_places=4)
    current_value  = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit           = models.CharField(max_length=50)
    deadline       = models.DateField()
    scope          = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    department     = models.ForeignKey('core.Department', null=True, blank=True, on_delete=models.SET_NULL)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def progress_percentage(self):
        if self.target_value == 0:
            return 0
        return min(float(self.current_value / self.target_value * 100), 100)

    def __str__(self):
        return self.title
