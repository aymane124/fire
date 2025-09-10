from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configuration du routeur pour l'API
router = DefaultRouter()
router.register(r'alerts', views.InterfaceAlertViewSet, basename='interface-alert')
router.register(r'status', views.InterfaceStatusViewSet, basename='interface-status')
router.register(r'executions', views.AlertExecutionViewSet, basename='alert-execution')

app_name = 'interface_monitor_service'

urlpatterns = [
    # Endpoints personnalisés (doivent venir AVANT le routeur)
    path('api/alerts/<uuid:pk>/test/', views.test_alert_view, name='test-alert'),
    path('api/alerts/<uuid:pk>/activate/', views.activate_alert, name='activate-alert'),
    path('api/alerts/<uuid:pk>/deactivate/', views.deactivate_alert, name='deactivate-alert'),
    path('api/alerts/<uuid:pk>/schedule/', views.schedule_alert, name='schedule-alert'),
    
    # Endpoints de surveillance
    path('api/monitoring/health/', views.monitoring_health, name='monitoring-health'),
    path('api/monitoring/status/', views.monitoring_status, name='monitoring-status'),
    path('api/monitoring/stats/', views.monitoring_stats, name='monitoring-stats'),
    path('api/monitoring/initialize/', views.initialize_monitoring, name='initialize-monitoring'),
    path('api/monitoring/start/', views.start_monitoring_system, name='start-monitoring'),
    
    # Endpoints de statistiques
    path('api/stats/summary/', views.stats_summary, name='stats-summary'),
    path('api/stats/firewall/<uuid:firewall_id>/', views.firewall_stats, name='firewall-stats'),
    path('api/stats/alert/<uuid:alert_id>/', views.alert_stats, name='alert-stats'),
    
    # Endpoints de gestion des tâches
    path('api/tasks/check-all/', views.check_all_alerts, name='check-all-alerts'),
    path('api/tasks/cleanup/', views.cleanup_old_executions, name='cleanup-executions'),
    
    # API REST (doit venir APRÈS les endpoints personnalisés)
    path('api/', include(router.urls)),
    
    # Interface web (si nécessaire)
    path('', views.InterfaceMonitorDashboard.as_view(), name='dashboard'),
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/create/', views.AlertCreateView.as_view(), name='alert-create'),
    path('alerts/<uuid:pk>/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<uuid:pk>/edit/', views.AlertUpdateView.as_view(), name='alert-update'),
    path('alerts/<uuid:pk>/delete/', views.AlertDeleteView.as_view(), name='alert-delete'),
]
