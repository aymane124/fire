from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.viewsets import ModelViewSet
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from .serializers import (
    ScreenshotRequestSerializer,
    ScreenshotResponseSerializer,
    ScreenshotReportSerializer,
)
from .models import ScreenshotReport
from .excel_generator import generate_excel_with_screenshot, cleanup_old_reports
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
        generate_excel = data.get('generate_excel', False)
        
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

                # Générer le fichier Excel si demandé
                if generate_excel:
                    try:
                        # Créer le rapport dans la base de données
                        report = ScreenshotReport.objects.create(
                            ip_address=ip_address,
                            protocol=protocol,
                            url=url,
                            screenshot_base64=result['image_base64'],
                            width=viewport_width,
                            height=viewport_height,
                            user=str(request.user) if request.user.is_authenticated else None
                        )
                        
                        # Générer le fichier Excel
                        filepath, filename = generate_excel_with_screenshot(
                            ip_address=ip_address,
                            protocol=protocol,
                            url=url,
                            screenshot_base64=result['image_base64'],
                            width=viewport_width,
                            height=viewport_height,
                            user=str(request.user) if request.user.is_authenticated else None
                        )
                        
                        if filepath:
                            # Mettre à jour le rapport avec le chemin du fichier
                            report.excel_file_path = filepath
                            report.save()
                            
                            # Ajouter les informations Excel à la réponse
                            response_payload['report_id'] = str(report.id)
                            response_payload['excel_download_url'] = f"/screenshots/download-excel/{report.id}/"
                            
                            logger.info(f"Fichier Excel généré: {filename}")
                        else:
                            logger.error("Échec de la génération du fichier Excel")
                            
                    except Exception as e:
                        logger.error(f"Erreur lors de la génération Excel: {e}")
                        # Continuer sans Excel si erreur

                out = ScreenshotResponseSerializer(response_payload)
                return Response(out.data, status=status.HTTP_200_OK)
            else:
                error_msg = result.get('error', 'Failed to capture screenshot')
                logger.error(f"Autonomous DelayCheckForti failed: {error_msg}")
                return Response({"detail": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as exc:
            logger.error(f"Error in autonomous DelayCheckForti: {exc}")
            return Response({"detail": f"Error capturing screenshot: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScreenshotReportViewSet(ModelViewSet):
    """
    ViewSet pour gérer les rapports de screenshots
    """
    queryset = ScreenshotReport.objects.all()
    serializer_class = ScreenshotReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les rapports par utilisateur si nécessaire"""
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            # Optionnel: filtrer par utilisateur
            # queryset = queryset.filter(user=str(self.request.user))
            pass
        return queryset


class DownloadExcelView(APIView):
    """
    Vue pour télécharger le fichier Excel généré
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, report_id):
        try:
            # Récupérer le rapport
            report = ScreenshotReport.objects.get(id=report_id)
            
            # Vérifier que le fichier existe
            if not report.excel_file_path or not os.path.exists(report.excel_file_path):
                raise Http404("Fichier Excel non trouvé")
            
            # Lire le fichier
            with open(report.excel_file_path, 'rb') as excel_file:
                response = HttpResponse(
                    excel_file.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # Nom du fichier pour le téléchargement
                filename = f"screenshot_report_{report.ip_address}_{report.created_at.strftime('%Y%m%d_%H%M%S')}.xlsx"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                logger.info(f"Fichier Excel téléchargé: {filename} par {request.user}")
                return response
                
        except ScreenshotReport.DoesNotExist:
            raise Http404("Rapport non trouvé")
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement Excel: {e}")
            return Response(
                {"detail": "Erreur lors du téléchargement du fichier"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CleanupReportsView(APIView):
    """
    Vue pour nettoyer les anciens rapports (admin seulement)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Vérifier les permissions admin (optionnel)
            if not request.user.is_staff:
                return Response(
                    {"detail": "Permissions insuffisantes"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            days_old = request.data.get('days_old', 7)
            cleanup_old_reports(days_old)
            
            return Response(
                {"detail": f"Nettoyage effectué pour les fichiers de plus de {days_old} jours"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
            return Response(
                {"detail": "Erreur lors du nettoyage"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
