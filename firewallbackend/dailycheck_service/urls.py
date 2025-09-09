from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyCheckViewSet

router = DefaultRouter()
router.register(r'daily-checks', DailyCheckViewSet, basename='daily-check')

urlpatterns = [
    path('', include(router.urls)),
] 