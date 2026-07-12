from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Department(models.Model):
    name       = models.CharField(max_length=150, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class ESGConfiguration(models.Model):
    env_weight  = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
    social_weight = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    gov_weight  = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    updated_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ESG Configuration'
        verbose_name_plural = 'ESG Configurations'

    def clean(self):
        total = self.env_weight + self.social_weight + self.gov_weight
        if total != 100:
            raise ValidationError("ESG weights must sum to exactly 100.")

    def save(self, *args, **kwargs):
        self.full_clean()  # enforces weight sum validation
        # Enforce singleton at database level
        if not self.pk:
            # Delete any existing configuration before creating a new one
            ESGConfiguration.objects.all().delete()
        else:
            ESGConfiguration.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config
