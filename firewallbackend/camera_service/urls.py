from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CameraViewSet

router = DefaultRouter()
router.register(r'cameras', CameraViewSet, basename='camera')

urlpatterns = [
    path('', include(router.urls)),
    path('upload_csv/', CameraViewSet.as_view({'post': 'upload_csv'}), name='camera-upload-csv'),
    path('ping-all/', CameraViewSet.as_view({'post': 'ping_all'}), name='camera-ping-all'),
] 