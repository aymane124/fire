from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import (
    ScreenshotRequestSerializer,
    ScreenshotResponseSerializer,
)
from auth_service.models import SSHUser
import logging

logger = logging.getLogger(__name__)


class CaptureScreenshotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ScreenshotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return self.handle_capture(request, data)

    def handle_capture(self, request, data):
        # data is already validated by ScreenshotRequestSerializer

        try:
            # Import DelayCheckForti script
            from .delaycheckforti import execute_autonomous_delaycheckforti
        except Exception as exc:
            return Response({"detail": f"Playwright not available: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Extraire les paramètres pour le script autonome
        ip_address = data.get('ip_address')
        protocol = data.get('protocol', 'https')
        path = data.get('path', '/login') or '/login'
        username = data.get('username') or ''
        password = data.get('password') or ''
        viewport_width = data.get('viewport_width', 1366)
        viewport_height = data.get('viewport_height', 768)
        timeout_ms = data.get('timeout_ms', 30000)
        ignore_https_errors = data.get('ignore_https_errors', True)
        
        # Auto-fill from SSHUser ONLY if both creds are missing; frontend overrides win
        if (not username and not password) and getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                ssh = SSHUser.objects.filter(user=request.user).first()
                if ssh:
                    username = username or ssh.ssh_username
                    try:
                        password = password or ssh.get_ssh_password()
                    except Exception:
                        # In case not prefixed or already plain
                        password = password or ssh.ssh_password
            except Exception:
                pass

        try:
            # Utiliser la fonction autonome DelayCheckForti
            logger.info("Executing autonomous DelayCheckForti script")
            result = execute_autonomous_delaycheckforti(
                ip_address=ip_address,
                protocol=protocol,
                path=path,
                username=username,
                password=password,
                timeout=timeout_ms,
                wait_after_popup=1000,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                ignore_https_errors=ignore_https_errors
            )
            
            if result['success'] and result['image_base64']:
                logger.info(f"Autonomous DelayCheckForti completed successfully. Steps: {result['steps_completed']}")
                
                # Construire l'URL pour la réponse
                url = f"{protocol}://{ip_address}{path}"
                
                response_payload = {
                    'image_base64': result['image_base64'],
                    'width': viewport_width,
                    'height': viewport_height,
                    'url': url,
                }

                out = ScreenshotResponseSerializer(response_payload)
                return Response(out.data, status=status.HTTP_200_OK)
            else:
                error_msg = result.get('error', 'Failed to capture screenshot')
                logger.error(f"Autonomous DelayCheckForti failed: {error_msg}")
                return Response({"detail": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as exc:
            logger.error(f"Error in autonomous DelayCheckForti: {exc}")
            return Response({"detail": f"Error capturing screenshot: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Les vues liées aux recettes ont été supprimées car le service fonctionne maintenant uniquement avec des scripts
