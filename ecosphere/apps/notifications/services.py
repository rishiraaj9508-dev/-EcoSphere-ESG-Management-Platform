from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, NotificationPreference, PlatformNotificationConfig

class NotificationService:
    @staticmethod
    def send(recipients, event_type, title, message):
        # Normalize recipients to a list
        if not hasattr(recipients, '__iter__') or isinstance(recipients, settings.AUTH_USER_MODEL.__class__):
            # Check if it is a single user object
            if hasattr(recipients, 'pk'):
                recipients = [recipients]
            else:
                recipients = list(recipients)

        platform_config = PlatformNotificationConfig.get_config()

        for user in recipients:
            # Fetch user preferences
            pref = NotificationPreference.objects.filter(user=user, event_type=event_type).first()
            
            in_app_allowed = pref.in_app_enabled if pref else True
            email_allowed  = pref.email_enabled if pref else True

            # 1. Create In-App Notification if enabled globally and by user
            if platform_config.global_in_app_enabled and in_app_allowed:
                Notification.objects.create(
                    user=user,
                    event_type=event_type,
                    title=title,
                    message=message
                )

            # 2. Dispatch Email if enabled globally and by user
            if platform_config.global_email_enabled and email_allowed and user.email:
                try:
                    send_mail(
                        subject=title,
                        message=message,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@ecosphere.com'),
                        recipient_list=[user.email],
                        fail_silently=True
                    )
                except Exception:
                    pass
