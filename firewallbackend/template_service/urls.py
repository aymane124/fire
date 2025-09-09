from django.urls import path
from .views import TemplateViewSet, VariableViewSet

template_detail = TemplateViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('', TemplateViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('<int:pk>/', template_detail),
    path('<int:pk>/add_variable/', TemplateViewSet.as_view({'post': 'add_variable'})),
    path('<int:pk>/remove_variable/', TemplateViewSet.as_view({'post': 'remove_variable'})),
    path('<int:pk>/download_excel/', TemplateViewSet.as_view({'get': 'download_excel'})),
    
    path('variables/', VariableViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('variables/<int:pk>/', VariableViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
]
