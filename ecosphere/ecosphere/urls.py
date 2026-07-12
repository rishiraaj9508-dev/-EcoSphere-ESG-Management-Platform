from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('apps.dashboard.urls')),
    path('core/', include('apps.core.urls')),
    path('environmental/', include('apps.environmental.urls')),
    path('social/', include('apps.social.urls')),
    path('governance/', include('apps.governance.urls')),
    path('gamification/', include('apps.gamification.urls')),
    path('reports/', include('apps.reports.urls')),
    path('notifications/', include('apps.notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
