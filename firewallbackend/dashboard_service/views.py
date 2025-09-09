from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

# Import des modèles
from firewall_service.models import Firewall
from datacenter_service.models import DataCenter
from auth_service.models import User
from command_service.models import FirewallCommand
from websocket_service.models import TerminalCommand

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Récupère toutes les statistiques du dashboard en une seule requête
    """
    try:
        # Récupérer les statistiques de base (filtrées par utilisateur)
        total_firewalls = Firewall.objects.filter(owner=request.user).count()
        active_firewalls = total_firewalls  # Tous les pare-feux sont considérés comme actifs pour l'instant
        
        # Data centers possédés par l'utilisateur
        total_datacenters = DataCenter.objects.filter(owner=request.user, is_active=True).count()
        
        # Commandes récentes de l'utilisateur (dernières 24h)
        yesterday = timezone.now() - timedelta(days=1)
        recent_commands = FirewallCommand.objects.filter(
            user=request.user,
            created_at__gte=yesterday
        ).count()
        
        # Tâches en attente de l'utilisateur (commandes en cours)
        pending_tasks = TerminalCommand.objects.filter(
            session__user=request.user,
            status='executing'
        ).count()
        
        # Déterminer la santé du système
        if active_firewalls > 0 and total_firewalls > 0:
            health_ratio = active_firewalls / total_firewalls
            if health_ratio >= 0.8:
                system_health = 'excellent'
            elif health_ratio >= 0.6:
                system_health = 'good'
            elif health_ratio >= 0.4:
                system_health = 'warning'
            else:
                system_health = 'critical'
        else:
            system_health = 'warning'
        
        # Données du dashboard
        dashboard_data = {
            'total_firewalls': total_firewalls,
            'active_firewalls': active_firewalls,
            'total_datacenters': total_datacenters,
            'recent_commands': recent_commands,
            'pending_tasks': pending_tasks,
            'system_health': system_health,
            'last_updated': timezone.now(),
            'user_info': {
                'username': request.user.username,
                'email': request.user.email,
                'is_staff': request.user.is_staff
            }
        }
        
        return Response({
            'success': True,
            'data': dashboard_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_dashboard_stats(request):
    """
    Statistiques enrichies pour les administrateurs:
    - Agrégats globaux
    - Activité récente des utilisateurs
    - Top utilisateurs par commandes
    - Sessions terminal actives
    """
    try:
        # Fenêtre de temps
        yesterday = timezone.now() - timedelta(days=1)
        last_7_days = timezone.now() - timedelta(days=7)

        # Agrégats globaux
        total_firewalls = Firewall.objects.count()
        total_datacenters = DataCenter.objects.filter(is_active=True).count()
        total_users = User.objects.filter(is_active=True).count()

        recent_commands_total = FirewallCommand.objects.filter(created_at__gte=yesterday).count()
        commands_last_7_days = FirewallCommand.objects.filter(created_at__gte=last_7_days).count()

        # Sessions en cours
        active_sessions = TerminalCommand.objects.filter(status='executing').count()

        # Top utilisateurs par volume de commandes (7 jours)
        from django.db.models import Count
        top_users = list(
            FirewallCommand.objects.filter(created_at__gte=last_7_days)
            .values('user__id', 'user__username')
            .annotate(command_count=Count('id'))
            .order_by('-command_count')[:10]
        )

        # Activité récente des utilisateurs (dernières 24h)
        recent_activity = list(
            FirewallCommand.objects.filter(created_at__gte=yesterday)
            .values('user__id', 'user__username')
            .annotate(commands=Count('id'))
            .order_by('-commands')
        )

        data = {
            'totals': {
                'firewalls': total_firewalls,
                'datacenters': total_datacenters,
                'users': total_users,
                'recent_commands_24h': recent_commands_total,
                'commands_last_7_days': commands_last_7_days,
                'active_terminal_commands': active_sessions,
            },
            'top_users_7d': top_users,
            'recent_activity_24h': recent_activity,
            'generated_at': timezone.now(),
        }

        return Response({'success': True, 'data': data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_quick_actions(request):
    """
    Récupère les actions rapides disponibles pour l'utilisateur
    """
    try:
        quick_actions = [
            {
                'id': 'create_firewall',
                'title': 'Créer un pare-feu',
                'description': 'Ajouter un nouveau pare-feu',
                'icon': 'shield-plus',
                'url': '/firewalls/create',
                'color': 'blue'
            },
            {
                'id': 'upload_csv',
                'title': 'Importer CSV',
                'description': 'Importer des pare-feux via CSV',
                'icon': 'upload',
                'url': '/settings',
                'color': 'green'
            },
            {
                'id': 'ping_all',
                'title': 'Ping tous',
                'description': 'Vérifier l\'état de tous les pare-feux',
                'icon': 'wifi',
                'url': '/firewalls',
                'color': 'orange'
            },
            {
                'id': 'view_logs',
                'title': 'Voir les logs',
                'description': 'Consulter l\'historique des actions',
                'icon': 'file-text',
                'url': '/logs',
                'color': 'purple'
            }
        ]
        
        return Response({
            'success': True,
            'data': quick_actions
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
