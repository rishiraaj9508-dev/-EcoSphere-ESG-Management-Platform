from django.db import models
from django.conf import settings

class Notification(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    event_type = models.CharField(max_length=50)  # POLICY_PUBLISHED, CHALLENGE_STATUS, etc.
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} (Read: {self.is_read})"


class NotificationPreference(models.Model):
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    event_type    = models.CharField(max_length=50)
    email_enabled = models.BooleanField(default=True)
    in_app_enabled= models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'event_type')

    def __str__(self):
        return f"{self.user.username} - {self.event_type} Pref"


class PlatformNotificationConfig(models.Model):
    global_email_enabled  = models.BooleanField(default=True)
    global_in_app_enabled = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return "Global Platform Notification Config"
