import logging
from typing import Dict, Any
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import InterfaceAlert, InterfaceStatus, AlertExecution
from .serializers import (
    InterfaceAlertSerializer, InterfaceStatusSerializer, 
    AlertExecutionSerializer, AlertCreateSerializer
)
from .tasks import (
    test_alert as task_test_alert, check_all_active_alerts, cleanup_old_executions,
    health_check, initialize_monitoring
)
from .services import InterfaceMonitorService

logger = logging.getLogger(__name__)


# Vues API REST
class InterfaceAlertViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des alertes d'interfaces via l'API REST"""
    
    queryset = InterfaceAlert.objects.all()
    serializer_class = InterfaceAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtre les alertes selon les permissions de l'utilisateur"""
        user = self.request.user
        
        if user.is_superuser:
            return InterfaceAlert.objects.select_related(
                'firewall', 'firewall__firewall_type', 'firewall__data_center', 'created_by'
            )
        else:
            return InterfaceAlert.objects.filter(
                Q(recipients=user) | Q(include_admin=True) | Q(include_superuser=True) | Q(created_by=user)
            ).select_related(
                'firewall', 'firewall__firewall_type', 'firewall__data_center', 'created_by'
            )
    
    def get_serializer_class(self):
        """Retourne le sérialiseur approprié selon l'action"""
        if self.action == 'create':
            return AlertCreateSerializer
        return InterfaceAlertSerializer
    
    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur créateur"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        alert = self.get_object()
        user = self.request.user
        if not (user.is_superuser or alert.created_by_id == user.id):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()
    
    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_superuser or instance.created_by_id == user.id):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Teste une alerte en l'exécutant immédiatement"""
        alert = self.get_object()
        
        # Vérifier les permissions
        if not request.user.is_superuser and request.user not in alert.recipients.all() and request.user != alert.created_by:
            return Response(
                {'error': 'Permission refusée'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Lancer le test directement
            result = task_test_alert(str(alert.id))
            
            return Response({
                'message': 'Test d\'alerte lancé',
                'status': 'completed',
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Erreur lors du test de l'alerte: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Active une alerte"""
        alert = self.get_object()
        user = request.user
        if not (user.is_superuser or alert.created_by_id == user.id):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            alert.is_active = True
            alert.save()
            
            # Programmer la première vérification
            from .tasks import schedule_next_check
            schedule_next_check(str(alert.id))
            
            return Response({'message': 'Alerte activée'})
            
        except Exception as e:
            logger.error(f"Erreur lors de l'activation: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Désactive une alerte"""
        alert = self.get_object()
        user = request.user
        if not (user.is_superuser or alert.created_by_id == user.id):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            alert.is_active = False
            alert.save()
            
            return Response({'message': 'Alerte désactivée'})
            
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_alerts(self, request):
        """Retourne les alertes de l'utilisateur connecté"""
        user = request.user
        
        if user.is_superuser:
            queryset = self.get_queryset()
        else:
            queryset = InterfaceAlert.objects.filter(
                Q(recipients=user) | Q(include_admin=True) | Q(include_superuser=True)
            ).select_related('firewall', 'firewall__firewall_type')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InterfaceStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour la consultation des statuts d'interfaces"""
    
    queryset = InterfaceStatus.objects.all()
    serializer_class = InterfaceStatusSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtre les statuts selon les permissions"""
        user = self.request.user
        
        if user.is_superuser:
            return InterfaceStatus.objects.select_related(
                'alert', 'alert__firewall'
            )
        else:
            return InterfaceStatus.objects.filter(
                Q(alert__recipients=user) | 
                Q(alert__include_admin=True) | 
                Q(alert__include_superuser=True)
            ).select_related('alert', 'alert__firewall')
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Retourne les derniers statuts d'interfaces"""
        queryset = self.get_queryset().order_by('-last_seen')[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_firewall(self, request):
        """Retourne les statuts groupés par firewall"""
        firewall_id = request.query_params.get('firewall_id')
        if not firewall_id:
            return Response(
                {'error': 'firewall_id requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(alert__firewall_id=firewall_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AlertExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour la consultation des exécutions d'alertes"""
    
    queryset = AlertExecution.objects.all()
    serializer_class = AlertExecutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtre les exécutions selon les permissions"""
        user = self.request.user
        
        if user.is_superuser:
            return AlertExecution.objects.select_related(
                'alert', 'alert__firewall'
            )
        else:
            return AlertExecution.objects.filter(
                Q(alert__recipients=user) | 
                Q(alert__include_admin=True) | 
                Q(alert__include_superuser=True)
            ).select_related('alert', 'alert__firewall')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Retourne les exécutions récentes"""
        hours = int(request.query_params.get('hours', 24))
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        
        queryset = self.get_queryset().filter(started_at__gte=cutoff)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Vues classiques Django
class InterfaceMonitorDashboard(LoginRequiredMixin, TemplateView):
    """Tableau de bord principal de surveillance des interfaces"""
    
    template_name = 'interface_monitor_service/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistiques générales
        if user.is_superuser:
            total_alerts = InterfaceAlert.objects.count()
            active_alerts = InterfaceAlert.objects.filter(is_active=True).count()
            recent_executions = AlertExecution.objects.filter(
                started_at__gte=timezone.now() - timezone.timedelta(hours=24)
            )
        else:
            total_alerts = InterfaceAlert.objects.filter(
                Q(recipients=user) | Q(include_admin=True) | Q(include_superuser=True)
            ).count()
            active_alerts = InterfaceAlert.objects.filter(
                Q(recipients=user) | Q(include_admin=True) | Q(include_superuser=True),
                is_active=True
            ).count()
            recent_executions = AlertExecution.objects.filter(
                Q(alert__recipients=user) | Q(alert__include_admin=True) | Q(alert__include_superuser=True),
                started_at__gte=timezone.now() - timezone.timedelta(hours=24)
            )
        
        # Calculer les statistiques
        successful_executions = recent_executions.filter(status='completed').count()
        failed_executions = recent_executions.filter(status='failed').count()
        success_rate = (successful_executions / (successful_executions + failed_executions) * 100) if (successful_executions + failed_executions) > 0 else 0
        
        context.update({
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'recent_executions_count': recent_executions.count(),
            'success_rate': round(success_rate, 2),
            'successful_executions': successful_executions,
            'failed_executions': failed_executions
        })
        
        return context


class AlertListView(LoginRequiredMixin, ListView):
    """Liste des alertes d'interfaces"""
    
    model = InterfaceAlert
    template_name = 'interface_monitor_service/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return InterfaceAlert.objects.select_related(
                'firewall', 'firewall__firewall_type', 'created_by'
            ).order_by('-created_at')
        else:
            return InterfaceAlert.objects.filter(
                Q(recipients=user) | Q(include_admin=True) | Q(include_superuser=True)
            ).select_related(
                'firewall', 'firewall__firewall_type', 'created_by'
            ).order_by('-created_at')


class AlertDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une alerte d'interface"""
    
    model = InterfaceAlert
    template_name = 'interface_monitor_service/alert_detail.html'
    context_object_name = 'alert'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ajouter les dernières exécutions
        context['recent_executions'] = self.object.executions.order_by('-started_at')[:10]
        
        # Ajouter les derniers statuts d'interfaces
        context['recent_status'] = self.object.status_checks.order_by('-last_seen')[:20]
        
        return context


class AlertCreateView(LoginRequiredMixin, CreateView):
    """Création d'une nouvelle alerte d'interface"""
    
    model = InterfaceAlert
    template_name = 'interface_monitor_service/alert_form.html'
    fields = [
        'name', 'description', 'firewall', 'alert_type', 'check_interval',
        'threshold_value', 'command_template', 'conditions', 'recipients',
        'include_admin', 'include_superuser', 'is_active'
    ]
    success_url = reverse_lazy('interface_monitor_service:alert-list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AlertUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modification d'une alerte d'interface"""
    
    model = InterfaceAlert
    template_name = 'interface_monitor_service/alert_form.html'
    fields = [
        'name', 'description', 'firewall', 'alert_type', 'check_interval',
        'threshold_value', 'command_template', 'conditions', 'recipients',
        'include_admin', 'include_superuser', 'is_active'
    ]
    success_url = reverse_lazy('interface_monitor_service:alert-list')
    
    def test_func(self):
        """Vérifie que l'utilisateur peut modifier cette alerte"""
        alert = self.get_object()
        user = self.request.user
        
        return user.is_superuser or user in alert.recipients.all()


class AlertDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Suppression d'une alerte d'interface"""
    
    model = InterfaceAlert
    template_name = 'interface_monitor_service/alert_confirm_delete.html'
    success_url = reverse_lazy('interface_monitor_service:alert-list')
    
    def test_func(self):
        """Vérifie que l'utilisateur peut supprimer cette alerte"""
        alert = self.get_object()
        user = self.request.user
        
        return user.is_superuser or user in alert.recipients.all()


# Vues de fonction pour les actions spécifiques (API DRF)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_alert_view(request, pk):
    """Teste une alerte d'interface (API)"""
    alert = get_object_or_404(InterfaceAlert, pk=pk)

    # Vérifier les permissions
    if not request.user.is_superuser and request.user not in alert.recipients.all():
        return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Lancer le test directement
        result = task_test_alert(str(alert.id))

        return Response({
            'success': True,
            'message': "Test d'alerte lancé",
            'result': result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur lors du test de l'alerte: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
@require_http_methods(['POST'])
def activate_alert(request, pk):
    """Active une alerte d'interface"""
    alert = get_object_or_404(InterfaceAlert, pk=pk)
    
    try:
        alert.is_active = True
        alert.save()
        
        # Programmer la première vérification
        from .tasks import schedule_next_check
        schedule_next_check(str(alert.id))
        
        return JsonResponse({'success': True, 'message': 'Alerte activée'})
        
    except Exception as e:
        logger.error(f"Erreur lors de l'activation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def deactivate_alert(request, pk):
    """Désactive une alerte d'interface"""
    alert = get_object_or_404(InterfaceAlert, pk=pk)
    
    try:
        alert.is_active = False
        alert.save()
        
        return JsonResponse({'success': True, 'message': 'Alerte désactivée'})
        
    except Exception as e:
        logger.error(f"Erreur lors de la désactivation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def schedule_alert(request, pk):
    """Programme la prochaine vérification d'une alerte"""
    alert = get_object_or_404(InterfaceAlert, pk=pk)
    
    try:
        from .tasks import schedule_next_check
        success = schedule_next_check(str(alert.id))
        
        if success:
            return JsonResponse({'success': True, 'message': 'Vérification programmée'})
        else:
            return JsonResponse({'error': 'Échec de la programmation'}, status=500)
        
    except Exception as e:
        logger.error(f"Erreur lors de la programmation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# Vues de surveillance
@login_required
def monitoring_health(request):
    """Vérifie la santé du système de surveillance"""
    try:
        # Lancer la vérification de santé
        result = health_check()
        
        return JsonResponse({
            'success': True,
            'message': 'Vérification de santé lancée',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de santé: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def monitoring_status(request):
    """Retourne le statut actuel du système de surveillance"""
    try:
        # Récupérer les statistiques en temps réel
        total_alerts = InterfaceAlert.objects.count()
        active_alerts = InterfaceAlert.objects.filter(is_active=True).count()
        
        # Dernières exécutions
        recent_executions = AlertExecution.objects.filter(
            started_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        
        successful = recent_executions.filter(status='completed').count()
        failed = recent_executions.filter(status='failed').count()
        running = recent_executions.filter(status='running').count()
        
        success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
        
        return JsonResponse({
            'status': 'healthy' if success_rate >= 80 else 'warning' if success_rate >= 50 else 'critical',
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'recent_executions': {
                'total': recent_executions.count(),
                'successful': successful,
                'failed': failed,
                'running': running,
                'success_rate': round(success_rate, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_stats(request):
    """Retourne les statistiques de surveillance pour le tableau de bord"""
    logger.info("monitoring_stats view called")  # Debug log
    
    try:
        # Statistiques des alertes
        total_alerts = InterfaceAlert.objects.count()
        active_alerts = InterfaceAlert.objects.filter(is_active=True).count()
        
        # Statistiques des exécutions (dernières 24h)
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        recent_executions = AlertExecution.objects.filter(started_at__gte=cutoff)
        total_executions = recent_executions.count()
        successful_executions = recent_executions.filter(status='completed').count()
        failed_executions = recent_executions.filter(status='failed').count()
        
        # Statistiques des alertes (dernières 24h)
        recent_alerts = InterfaceAlert.objects.filter(created_at__gte=cutoff).count()
        
        # Pour l'instant, on simule les emails envoyés (à implémenter plus tard)
        total_emails_sent = 0
        
        logger.info(f"monitoring_stats returning data: {total_alerts} alerts, {total_executions} executions")  # Debug log
        
        return JsonResponse({
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'total_emails_sent': total_emails_sent,
            'last_24h_executions': total_executions,
            'last_24h_alerts': recent_alerts
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques de surveillance: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def initialize_monitoring(request):
    """Initialise le système de surveillance"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    try:
        # Lancer l'initialisation
        result = initialize_monitoring()
        
        return JsonResponse({
            'success': True,
            'message': 'Initialisation lancée',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# Vues de statistiques
@login_required
def stats_summary(request):
    """Retourne un résumé des statistiques"""
    try:
        # Statistiques des alertes
        alerts_stats = InterfaceAlert.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            by_type=Count('id', filter=Q(alert_type='interface_down'))
        )
        
        # Statistiques des exécutions (dernières 24h)
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        executions_stats = AlertExecution.objects.filter(
            started_at__gte=cutoff
        ).aggregate(
            total=Count('id'),
            successful=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            avg_duration=Avg('duration')
        )
        
        return JsonResponse({
            'alerts': alerts_stats,
            'executions': executions_stats,
            'period': '24h'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def firewall_stats(request, firewall_id):
    """Retourne les statistiques pour un firewall spécifique"""
    try:
        # Récupérer les alertes du firewall
        alerts = InterfaceAlert.objects.filter(firewall_id=firewall_id)
        
        # Statistiques des alertes
        alerts_count = alerts.count()
        active_alerts = alerts.filter(is_active=True).count()
        
        # Dernières exécutions
        recent_executions = AlertExecution.objects.filter(
            alert__firewall_id=firewall_id,
            started_at__gte=timezone.now() - timezone.timedelta(hours=24)
        )
        
        successful = recent_executions.filter(status='completed').count()
        failed = recent_executions.filter(status='failed').count()
        
        return JsonResponse({
            'firewall_id': str(firewall_id),
            'alerts': {
                'total': alerts_count,
                'active': active_alerts
            },
            'executions': {
                'total': recent_executions.count(),
                'successful': successful,
                'failed': failed,
                'success_rate': round((successful / (successful + failed) * 100) if (successful + failed) > 0 else 0, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques du firewall: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def alert_stats(request, alert_id):
    """Retourne les statistiques pour une alerte spécifique"""
    try:
        alert = get_object_or_404(InterfaceAlert, pk=alert_id)
        
        # Vérifier les permissions
        if not request.user.is_superuser and request.user not in alert.recipients.all():
            return JsonResponse({'error': 'Permission refusée'}, status=403)
        
        # Statistiques des exécutions
        executions = alert.executions.all()
        total_executions = executions.count()
        successful = executions.filter(status='completed').count()
        failed = executions.filter(status='failed').count()
        
        # Derniers statuts d'interfaces
        recent_status = alert.status_checks.order_by('-last_seen')[:10]
        
        return JsonResponse({
            'alert_id': str(alert_id),
            'alert_name': alert.name,
            'executions': {
                'total': total_executions,
                'successful': successful,
                'failed': failed,
                'success_rate': round((successful / total_executions * 100) if total_executions > 0 else 0, 2)
            },
            'recent_status': list(recent_status.values('interface_name', 'status', 'last_seen'))
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques de l'alerte: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# Vues de gestion des tâches
@login_required
def check_all_alerts(request):
    """Lance la vérification de toutes les alertes actives"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    try:
        # Lancer la vérification
        result = check_all_active_alerts()
        
        return JsonResponse({
            'success': True,
            'message': 'Vérification de toutes les alertes lancée',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de toutes les alertes: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def cleanup_old_executions(request):
    """Lance le nettoyage des anciennes exécutions"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    try:
        days = int(request.GET.get('days', 30))
        
        # Lancer le nettoyage
        result = cleanup_old_executions(days)
        
        return JsonResponse({
            'success': True,
            'message': f'Nettoyage des exécutions de plus de {days} jours lancé',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def start_monitoring_system(request):
    """Démarre le système de monitoring des interfaces"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    try:
        from .tasks import start_monitoring_system
        
        # Démarrer le système de monitoring
        result = start_monitoring_system()
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': 'Système de monitoring démarré avec succès',
                'result': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Erreur inconnue')
            }, status=500)
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du système de monitoring: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)



