from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FirewallViewSet, FirewallTypeViewSet

router = DefaultRouter()
router.register(r'firewalls', FirewallViewSet, basename='firewall')
router.register(r'firewall-types', FirewallTypeViewSet, basename='firewall-type')

app_name = 'firewall_service'

urlpatterns = [
    path('', include(router.urls)),
    path('<uuid:pk>/ping/', FirewallViewSet.as_view({'post': 'ping'}), name='firewall-ping'),
    path('ping_all/', FirewallViewSet.as_view({'post': 'ping_all'}), name='firewall-ping-all'),
    path('upload-csv/', FirewallViewSet.as_view({'post': 'upload_csv'}), name='firewall-upload-csv'),
] 