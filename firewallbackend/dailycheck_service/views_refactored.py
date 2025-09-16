"""
Vues refactorisées pour le service dailycheck
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import os
import logging

from .models import DailyCheck, CheckCommand
from .serializers import DailyCheckSerializer, CheckCommandSerializer
from .services.task_manager import task_manager
from .services.ssh_executor import SSHExecutor
from .services.excel_generator import ExcelGenerator
from .utils.validation_utils import ValidationUtils
from .screenshot_integration import capture_firewall_screenshot_with_fallback

logger = logging.getLogger(__name__)

class DailyCheckViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les daily checks
    """
    serializer_class = DailyCheckSerializer

    def get_queryset(self):
        """Filtre les daily checks par utilisateur"""
        daily_checks = DailyCheck.objects.all()
        user_checks = []
        
        for check in daily_checks:
            # Vérifier si l'historique contient l'utilisateur actuel
            if check.historique_dailycheck and 'entries' in check.historique_dailycheck:
                for entry in check.historique_dailycheck['entries']:
                    if entry.get('user') == str(self.request.user):
                        user_checks.append(check)
                        break
        
        return DailyCheck.objects.filter(id__in=[check.id for check in user_checks])

    def perform_create(self, serializer):
        """Crée un daily check avec historique"""
        instance = serializer.save()
        instance.add_to_history(
            action='create',
            status='success',
            details=f"Daily check created for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        """Met à jour un daily check avec historique"""
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f"Daily check updated for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        """Supprime un daily check avec historique"""
        instance.add_to_history(
            action='delete',
            status='success',
            details=f"Daily check deleted for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def run_commands(self, request, pk=None):
        """
        Exécute des commandes pour un daily check spécifique
        """
        daily_check = self.get_object()
        firewall = daily_check.firewall
        
        try:
            # Valider les données
            commands = request.data.get('commands', [])
            validation = ValidationUtils.validate_commands(commands)
            
            if not validation['valid']:
                return Response(
                    {'error': validation['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Capturer le screenshot
            logger.info(f"Capturing screenshot for firewall {firewall.name}")
            screenshot_result = capture_firewall_screenshot_with_fallback(firewall, request.user)
            
            if screenshot_result['success']:
                daily_check.screenshot_base64 = screenshot_result['screenshot_base64']
                daily_check.screenshot_captured = True
                logger.info(f"Screenshot captured for firewall {firewall.name}")
            else:
                logger.warning(f"Screenshot capture failed for firewall {firewall.name}: {screenshot_result.get('error', 'Unknown error')}")
            
            daily_check.save()
            
            # Exécuter les commandes SSH
            ssh_executor = SSHExecutor()
            results = ssh_executor.execute_commands_in_session(firewall, commands, request.user)
            
            # Créer les enregistrements CheckCommand
            check_results = []
            for cmd_result in results:
                command_result = CheckCommand.objects.create(
                    daily_check=daily_check,
                    command=cmd_result['command'],
                    actual_output=cmd_result['output'] if cmd_result['status'] == 'completed' else cmd_result['error'],
                    status='SUCCESS' if cmd_result['status'] == 'completed' else 'FAILED'
                )
                command_result.add_to_history(
                    action='create',
                    status='success' if cmd_result['status'] == 'completed' else 'failed',
                    details=f"Command executed: {cmd_result['command']}",
                    user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                check_results.append(command_result)
            
            # Générer le fichier Excel
            excel_generator = ExcelGenerator()
            filepath = excel_generator.generate_report(daily_check, results, firewall)
            
            # Mettre à jour le statut
            daily_check.excel_report = filepath
            daily_check.status = 'SUCCESS'
            for res in check_results:
                if res.status == 'FAILED':
                    daily_check.status = 'FAILED'
                    break

            daily_check.save()
            daily_check.add_to_history(
                action='run_commands',
                status='success' if daily_check.status == 'SUCCESS' else 'failed',
                details=f"Daily check completed with {len(check_results)} commands",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'status': daily_check.status,
                'message': 'Daily check completed and report generated',
                'report_path': filepath
            })
            
        except Exception as e:
            logger.error(f"Error in run_commands: {str(e)}")
            daily_check.status = 'FAILED'
            daily_check.notes = str(e)
            daily_check.save()
            daily_check.add_to_history(
                action='run_commands',
                status='failed',
                details=f"Error during daily check: {str(e)}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_reports(self, request):
        """Récupère tous les rapports disponibles"""
        reports = DailyCheck.objects.filter(excel_report__isnull=False)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download_report(self, request, pk=None):
        """Télécharge un rapport Excel"""
        daily_check = self.get_object()
        if not daily_check.excel_report:
            return Response({
                'error': 'No report available for this daily check'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(daily_check.excel_report, 'rb') as file:
                file_content = file.read()
            response = HttpResponse(
                file_content, 
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(daily_check.excel_report)}"'
            
            daily_check.add_to_history(
                action='download_report',
                status='success',
                details=f"Report downloaded: {os.path.basename(daily_check.excel_report)}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return response
        except Exception as e:
            daily_check.add_to_history(
                action='download_report',
                status='failed',
                details=f"Error downloading report: {str(e)}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def run_multiple_checks(self, request):
        """Lance des daily checks pour plusieurs firewalls"""
        try:
            firewall_ids = request.data.get('firewalls', [])
            commands = request.data.get('commands', [])
            
            # Valider les données
            if not firewall_ids or not commands:
                return Response(
                    {'error': 'No firewalls or commands provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Récupérer les firewalls
            from command_service.models import Firewall
            firewalls = list(Firewall.objects.filter(id__in=firewall_ids))
            
            # Valider les firewalls
            validation = ValidationUtils.validate_firewalls(firewalls)
            if not validation['valid']:
                return Response(
                    {'error': validation['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Valider les commandes
            validation = ValidationUtils.validate_commands(commands)
            if not validation['valid']:
                return Response(
                    {'error': validation['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ajouter la tâche à la queue
            task_id = task_manager.add_task(firewalls, commands, request.user)
            
            return Response({
                'status': 'success',
                'message': 'Daily checks started',
                'task_id': task_id
            })
            
        except Exception as e:
            logger.error(f"Error in run_multiple_checks: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def check_task_status(self, request):
        """Vérifie le statut d'une tâche"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({
                'error': 'No task ID provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        status_info = task_manager.get_task_status(task_id)
        if status_info['status'] == 'not_found':
            return Response({
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(status_info)

    @action(detail=False, methods=['get'])
    def download_multiple_reports(self, request):
        """Télécharge un rapport multiple"""
        try:
            report_path = request.query_params.get('report_path')
            if not report_path:
                return Response({
                    'error': 'No report path provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not os.path.exists(report_path):
                return Response({
                    'error': 'Report file not found'
                }, status=status.HTTP_404_NOT_FOUND)

            with open(report_path, 'rb') as file:
                file_content = file.read()
            response = HttpResponse(
                file_content, 
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_path)}"'
            
            # Ajouter à l'historique pour tous les daily checks liés
            daily_checks = DailyCheck.objects.filter(excel_report=report_path)
            for daily_check in daily_checks:
                daily_check.add_to_history(
                    action='download_multiple_reports',
                    status='success',
                    details=f"Multiple reports downloaded: {os.path.basename(report_path)}",
                    user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return response
        except Exception as e:
            logger.error(f"Error in download_multiple_reports: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
