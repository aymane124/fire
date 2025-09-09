from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataCenterViewSet

router = DefaultRouter()
router.register(r'', DataCenterViewSet, basename='datacenter')

app_name = 'datacenter_service'

urlpatterns = [
    path('', include(router.urls)),
]
