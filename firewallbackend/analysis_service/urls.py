from django.urls import path
from .views import FlowMatrixView

urlpatterns = [
    path('flow-matrix/analyze-ip/', FlowMatrixView.as_view(), name='flow-matrix-analyze-ip'),
] 