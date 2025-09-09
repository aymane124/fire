from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FirewallConfigViewSet

router = DefaultRouter()
router.register(r'configs', FirewallConfigViewSet, basename='firewall-config')

app_name = 'config_service'

urlpatterns = [
    path('', include(router.urls)),
] 