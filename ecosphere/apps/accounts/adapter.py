from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        # By default redirect all roles to the main dashboard,
        # which will perform role-based data scoping internally.
        return reverse('dashboard:main')
