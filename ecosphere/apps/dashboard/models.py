from django.db import models

class DepartmentESGScore(models.Model):
    department          = models.OneToOneField('core.Department', on_delete=models.CASCADE, related_name='esg_score')
    environmental_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    social_score        = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    governance_score    = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    overall_score       = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    last_calculated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.department.name} - Overall: {self.overall_score}"
