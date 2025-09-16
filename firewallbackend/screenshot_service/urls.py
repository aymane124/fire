from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaptureScreenshotView,
    ScreenshotReportViewSet,
    DownloadExcelView,
    CleanupReportsView
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'reports', ScreenshotReportViewSet, basename='screenshot-reports')

urlpatterns = [
    # Capture de screenshot
    path('capture/', CaptureScreenshotView.as_view(), name='capture-screenshot'),
    
    # Téléchargement Excel
    path('download-excel/<uuid:report_id>/', DownloadExcelView.as_view(), name='download-excel'),
    
    # Nettoyage des rapports (admin)
    path('cleanup/', CleanupReportsView.as_view(), name='cleanup-reports'),
    
    # Inclure les routes du router
    path('', include(router.urls)),
]

