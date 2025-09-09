from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceHistoryViewSet

router = DefaultRouter()
router.register(r'', ServiceHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 