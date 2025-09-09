from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmailLogViewSet, AdminSendEmailView, AutomatedEmailScheduleViewSet,
    AutomatedEmailExecutionViewSet, CommandExecutionResultViewSet,
    CommandTemplateViewSet
)

router = DefaultRouter()
router.register(r'logs', EmailLogViewSet)
router.register(r'schedules', AutomatedEmailScheduleViewSet, basename='schedule')
router.register(r'executions', AutomatedEmailExecutionViewSet, basename='execution')
router.register(r'command-results', CommandExecutionResultViewSet, basename='command-result')
router.register(r'command-templates', CommandTemplateViewSet, basename='command-template')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/send-email/', AdminSendEmailView.as_view(), name='admin_send_email'),
] 