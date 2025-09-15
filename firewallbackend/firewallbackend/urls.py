from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from .csrf_views import get_csrf_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/csrf/', get_csrf_token),  # Add CSRF endpoint

    # all your existing API endpoints:
    path('api/auth/',       include('auth_service.urls')),
    path('api/firewalls/',  include('firewall_service.urls')),
    path('api/datacenters/',include('datacenter_service.urls')),
    path('api/config/',     include('config_service.urls')),
    path('api/analysis/',   include('analysis_service.urls')),
    path('api/command/',    include('command_service.urls')),
    path('api/cameras/',    include('camera_service.urls')),
    path('api/templates/',  include('template_service.urls')),
    path('api/daily-check/', include('dailycheck_service.urls')),
    path('api/history/',    include('history_service.urls')),
    path('api/email/',      include('email_service.urls')),
    path('api/interface-monitor/', include('interface_monitor_service.urls')),
    path('api/screenshots/', include('screenshot_service.urls')),

    path('api/dashboard/',  include('dashboard_service.urls')),
]

# Catch-all route for React - must be last
urlpatterns += [
    re_path(r'^(?!api/).*$', TemplateView.as_view(template_name='index.html')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
