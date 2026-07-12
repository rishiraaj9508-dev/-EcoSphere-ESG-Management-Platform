from django.db import models
from django.conf import settings

class CustomReportAudit(models.Model):
    generated_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    modules       = models.JSONField()  # e.g., ["environmental", "social", "governance"]
    date_from     = models.DateField()
    date_to       = models.DateField()
    departments   = models.ManyToManyField('core.Department')
    export_format = models.CharField(max_length=10)  # csv, excel, pdf
    generated_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.generated_by.username if self.generated_by else "System"
        return f"Report by {username} at {self.generated_at}"
