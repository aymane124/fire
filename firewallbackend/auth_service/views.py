from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.conf import settings
import logging
import paramiko

from .models import User, SSHUser
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer, 
    SSHUserSerializer,
    CustomTokenRefreshSerializer
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .utils.crypto import encrypt_user_data, encrypt_ssh_data
from .security import (
    validate_password_complexity,
    check_login_attempts,
    increment_login_attempts,
    reset_login_attempts,
    blacklist_token,
    is_token_blacklisted,
    rotate_refresh_token
)

logger = logging.getLogger(__name__)

# Create your views here.

@api_view(['GET'])
@ensure_csrf_cookie
def get_csrf_token(request):
    """
    View to set CSRF cookie. This view should be called before any POST request.
    """
    token = get_token(request)
    response = JsonResponse({
        "detail": "CSRF cookie set.",
        "token": token
    })
    response.set_cookie(
        'csrftoken',
        token,
        max_age=60 * 60 * 2,  # 2 hours (plus sécurisé)
        secure=not settings.DEBUG,  # True en production
        httponly=False,  # Permettre l'accès JavaScript pour l'authentification
        samesite='Lax',  # Plus permissif pour l'authentification
        path='/'
    )
    return response

class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # No authentication required for login

    @method_decorator(ensure_csrf_cookie)
    @action(detail=False, methods=['get'])
    def csrf(self, request):
        token = get_token(request)
        response = Response({
            'detail': 'CSRF cookie set',
            'token': token
        })
        response.set_cookie(
            'csrftoken',
            token,
            max_age=60 * 60 * 2,  # 2 hours (plus sécurisé)
            secure=not settings.DEBUG,  # True en production
            httponly=False,  # Permettre l'accès JavaScript pour l'authentification
            samesite='Lax',  # Plus permissif pour l'authentification
            path='/'
        )
        return response

    @method_decorator(ensure_csrf_cookie)
    @method_decorator(never_cache)
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Validate password complexity
            password = serializer.validated_data.get('password')
            is_valid, message = validate_password_complexity(password)
            if not is_valid:
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user
            user = serializer.save()
            
            # Create SSH user with the same credentials
            try:
                ssh_user = SSHUser.objects.get(user=user)
                # Set the SSH password to be the same as the user password
                ssh_user.set_ssh_password(password)
                logger.info(f"SSH password set for user {user.username}")
            except SSHUser.DoesNotExist:
                # Create SSH user if it doesn't exist (fallback)
                ssh_user = SSHUser.objects.create(
                    user=user,
                    ssh_username=user.username
                )
                ssh_user.set_ssh_password(password)
                logger.info(f"SSH user created and password set for user {user.username}")
            except Exception as e:
                logger.error(f"Error creating SSH user for {user.username}: {str(e)}")
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(ensure_csrf_cookie)
    @action(detail=False, methods=['post'])
    def login(self, request):
        logger.info("Login attempt received")
        serializer = UserLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"Invalid login data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        # Check login attempts
        if not check_login_attempts(username):
            return Response(
                {'error': 'Too many login attempts. Please try again later.'}, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        logger.info(f"Login attempt for user: {username}")
        user = authenticate(username=username, password=password)
        
        if user is None:
            increment_login_attempts(username)
            logger.warning(f"Authentication failed for user: {username}")
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # Reset login attempts on successful login
        reset_login_attempts(username)
        logger.info(f"User authenticated successfully: {username}")
        
        # Ensure SSH user exists for this user
        try:
            ssh_user = SSHUser.objects.get(user=user)
        except SSHUser.DoesNotExist:
            # Create SSH user if it doesn't exist
            ssh_user = SSHUser.objects.create(
                user=user,
                ssh_username=user.username
            )
            # Set SSH password to be the same as user password (temporary solution)
            # In a real scenario, you might want to prompt the user to set a separate SSH password
            ssh_user.set_ssh_password(password)
            logger.info(f"SSH user created for existing user {username}")
        
        refresh = RefreshToken.for_user(user)
        # Determine role
        role = 'admin' if user.is_staff else 'user'
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': role,
        })

    @action(detail=False, methods=['post'])
    def verify_token(self, request):
        try:
            token = request.data.get('token')
            if not token:
                return Response({'valid': False, 'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if is_token_blacklisted(token):
                return Response({'valid': False, 'error': 'Token is blacklisted'}, status=status.HTTP_401_UNAUTHORIZED)
                
            RefreshToken(token)
            return Response({'valid': True})
        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return Response({'valid': False, 'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                blacklist_token(refresh_token)
            return Response({'message': 'Successfully logged out'})
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.all()  # Superuser: all users
        return self.queryset.filter(id=user.id)  # Others: only self

    def _forbid_if_target_is_superuser_and_requester_is_not(self, request, target_user):
        if target_user.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Only a superuser can modify another superuser.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def update(self, request, *args, **kwargs):
        target_user = self.get_object()
        # Non-superusers cannot modify another user's profile
        if not request.user.is_superuser and target_user.id != request.user.id:
            return Response({'detail': 'Only superusers can modify other users.'}, status=status.HTTP_403_FORBIDDEN)
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, target_user)
        if forbidden:
            return forbidden
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        target_user = self.get_object()
        if not request.user.is_superuser and target_user.id != request.user.id:
            return Response({'detail': 'Only superusers can modify other users.'}, status=status.HTTP_403_FORBIDDEN)
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, target_user)
        if forbidden:
            return forbidden
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        target_user = self.get_object()
        if not request.user.is_superuser and target_user.id != request.user.id:
            return Response({'detail': 'Only superusers can delete other users.'}, status=status.HTTP_403_FORBIDDEN)
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, target_user)
        if forbidden:
            return forbidden
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # Only superusers can create users via this endpoint; regular registration remains under auth/register
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can create users here.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get', 'delete'])
    def me(self, request):
        """
        Get or delete the current user's profile
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'DELETE':
            try:
                user = request.user
                logger.info(f"Deleting user profile: {user.username}")
                
                # Get user ID before deletion for logging
                user_id = user.id
                username = user.username
                
                # Delete associated SSH users first
                SSHUser.objects.filter(user=user).delete()
                
                # Delete user's groups and permissions
                user.groups.clear()
                user.user_permissions.clear()
                
                # Delete the user
                user.delete()
                
                logger.info(f"User profile deleted successfully: {username} (ID: {user_id})")
                return Response({
                    'message': 'Votre compte a été supprimé avec succès'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error deleting user profile: {str(e)}")
                return Response({
                    'error': 'Une erreur est survenue lors de la suppression du profil'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def create_ssh_user(self, request):
        """
        Create SSH user for the current user if it doesn't exist
        """
        try:
            user = request.user
            password = request.data.get('password')
            
            if not password:
                return Response({
                    'error': 'Password is required to create SSH user'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if SSH user already exists
            try:
                ssh_user = SSHUser.objects.get(user=user)
                return Response({
                    'message': 'SSH user already exists',
                    'ssh_username': ssh_user.ssh_username
                })
            except SSHUser.DoesNotExist:
                # Create new SSH user
                ssh_user = SSHUser.objects.create(
                    user=user,
                    ssh_username=user.username
                )
                ssh_user.set_ssh_password(password)
                
                logger.info(f"SSH user created for user {user.username}")
                return Response({
                    'message': 'SSH user created successfully',
                    'ssh_username': ssh_user.ssh_username
                })
                
        except Exception as e:
            logger.error(f"Error creating SSH user: {str(e)}")
            return Response({
                'error': f'Failed to create SSH user: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['put'])
    def update_user_info(self, request):
        """
        Update user information including password
        """
        user = request.user
        logger.info(f"Updating user profile for user: {user.username}")
        logger.info(f"Request data: {request.data}")
        
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            logger.info("Serializer is valid")
            # Validate password complexity if password is being updated
            if 'password' in request.data and request.data['password']:
                password = request.data['password']
                logger.info("Password update requested")
                is_valid, message = validate_password_complexity(password)
                if not is_valid:
                    logger.warning(f"Password validation failed: {message}")
                    return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Update user using serializer
                updated_user = serializer.save()
                logger.info("User profile updated successfully")
                
                return Response({
                    'message': 'User information updated successfully',
                    'user': serializer.data
                })
            except Exception as e:
                logger.error(f"Error updating user profile: {str(e)}")
                return Response({
                    'error': 'Une erreur est survenue lors de la mise à jour du profil'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.warning(f"Invalid update data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def freeze(self, request, pk=None):
        """Freeze (disable) a user account (set is_active to False)."""
        user = self.get_object()
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can freeze accounts.'}, status=status.HTTP_403_FORBIDDEN)
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, user)
        if forbidden:
            return forbidden
        user.is_active = False
        user.save()
        return Response({'status': 'user frozen'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unfreeze(self, request, pk=None):
        """Unfreeze (enable) a user account (set is_active to True)."""
        user = self.get_object()
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can unfreeze accounts.'}, status=status.HTTP_403_FORBIDDEN)
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, user)
        if forbidden:
            return forbidden
        user.is_active = True
        user.save()
        return Response({'status': 'user unfrozen'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def promote_to_admin(self, request, pk=None):
        """Promote a user to admin (set is_staff to True)."""
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can promote to admin.'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, user)
        if forbidden:
            return forbidden
        user.is_staff = True
        user.save()
        return Response({'status': 'user promoted to admin'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def demote_from_admin(self, request, pk=None):
        """Demote an admin to regular user (set is_staff to False)."""
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can demote admins.'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        forbidden = self._forbid_if_target_is_superuser_and_requester_is_not(request, user)
        if forbidden:
            return forbidden
        user.is_staff = False
        user.save()
        return Response({'status': 'user demoted from admin'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def promote_to_superuser(self, request, pk=None):
        """Promote a user to superuser (set is_superuser to True)."""
        target_user = self.get_object()
        # Only allow current superusers to elevate others
        if not request.user.is_superuser:
            return Response({'detail': 'Superuser privileges required.'}, status=status.HTTP_403_FORBIDDEN)
        target_user.is_superuser = True
        target_user.is_staff = True
        target_user.save()
        return Response({'status': 'user promoted to superuser'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def demote_from_superuser(self, request, pk=None):
        """Demote a superuser to admin (set is_superuser to False)."""
        target_user = self.get_object()
        # Only allow current superusers to demote superusers, and avoid self-demotion lockouts if desired
        if not request.user.is_superuser:
            return Response({'detail': 'Superuser privileges required.'}, status=status.HTTP_403_FORBIDDEN)
        # Prevent removing the last remaining superuser
        if target_user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            return Response({'detail': 'Cannot demote the last superuser.'}, status=status.HTTP_400_BAD_REQUEST)
        target_user.is_superuser = False
        # Keep is_staff as True so they remain admin, unless explicitly changed elsewhere
        target_user.save()
        return Response({'status': 'user demoted from superuser'})

class SSHUserViewSet(viewsets.ModelViewSet):
    queryset = SSHUser.objects.all()
    serializer_class = SSHUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Chiffrer le mot de passe SSH avant de sauvegarder
        raw_password = serializer.validated_data.get('ssh_password')
        if raw_password:
            encrypted_password = encrypt_ssh_data(raw_password)
            serializer.validated_data['ssh_password'] = encrypted_password
        
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_ssh_users(self, request):
        ssh_users = self.get_queryset()
        page = self.paginate_queryset(ssh_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(ssh_users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        ssh_user = self.get_object()
        try:
            # Récupérer le mot de passe déchiffré
            decrypted_password = ssh_user.get_ssh_password()
            
            # Tester la connexion SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Utiliser les credentials pour tester la connexion
            ssh.connect(
                'localhost',  # À remplacer par l'adresse du serveur SSH
                username=ssh_user.ssh_username,
                password=decrypted_password,
                timeout=5
            )
            
            ssh.close()
            return Response({
                'status': 'success', 
                'message': 'Connection successful'
            })
        except Exception as e:
            logger.error(f"SSH connection test failed: {str(e)}")
            return Response({
                'status': 'error', 
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view that uses the custom serializer
    """
    serializer_class = CustomTokenRefreshSerializer
