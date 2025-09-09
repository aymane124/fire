from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, UserViewSet, SSHUserViewSet, get_csrf_token, CustomTokenRefreshView

router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='user')
router.register(r'ssh-users', SSHUserViewSet, basename='ssh-user')

app_name = 'auth_service'

urlpatterns = [
    path('', include(router.urls)),
    path('csrf/', get_csrf_token, name='get_csrf_token'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
] 