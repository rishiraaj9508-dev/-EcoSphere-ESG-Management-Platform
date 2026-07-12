from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('esg_manager', 'ESG Manager'),
        ('dept_head',   'Department Head'),
        ('employee',    'Employee'),
    ]
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.ForeignKey('core.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='members')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
