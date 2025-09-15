from django.urls import path
from .views import CaptureScreenshotView


urlpatterns = [
    path('capture/', CaptureScreenshotView.as_view(), name='capture-screenshot'),
]

