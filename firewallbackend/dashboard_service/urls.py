from django.urls import path
from . import views

app_name = 'dashboard_service'

urlpatterns = [
    path('stats/', views.dashboard_stats, name='dashboard-stats'),
    path('quick-actions/', views.dashboard_quick_actions, name='dashboard-quick-actions'),
    path('admin-stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
]
