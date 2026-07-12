from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = []

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        profile = getattr(self.request.user, 'profile', None)
        if not profile:
            return False
        return profile.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You do not have permission to view this resource.")
        return super().handle_no_permission()
