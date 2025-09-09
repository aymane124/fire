from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FirewallCommandViewSet, ExecuteCommandView

router = DefaultRouter()
router.register(r'commands', FirewallCommandViewSet, basename='firewall-command')

app_name = 'command_service'

urlpatterns = [
    path('', include(router.urls)),
    path('execute/', ExecuteCommandView.as_view(), name='execute-command'),
    path('commands/execute-multiple/', FirewallCommandViewSet.as_view({'post': 'execute_multiple'}), name='execute-multiple-commands'),
    path('commands/save-config/', FirewallCommandViewSet.as_view({'post': 'save_config'}), name='save-config'),
] 