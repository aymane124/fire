import logging
import asyncio
from typing import List, Dict, Any
from django.utils import timezone
from django.conf import settings
# from celery import shared_task
# from celery.utils.log import get_task_logger
from .models import InterfaceAlert, AlertExecution
from .services import InterfaceMonitorService
import threading
import time

# Simple background runner control
_RUNNER_STARTED = False

# logger = get_task_logger(__name__)
logger = logging.getLogger(__name__)


# @shared_task(bind=True, name='interface_monitor.check_interfaces')
def check_firewall_interfaces(alert_id: str) -> Dict[str, Any]:
    """
    Tâche pour vérifier les interfaces d'un firewall
    
    Args:
        alert_id: ID de l'alerte à vérifier
        
    Returns:
        Résultat de la vérification
    """
    try:
        logger.info(f"Début de la vérification des interfaces pour l'alerte: {alert_id}")
        
        # Récupérer l'alerte
        try:
            alert = InterfaceAlert.objects.get(id=alert_id, is_active=True)
        except InterfaceAlert.DoesNotExist:
            logger.error(f"Alerte {alert_id} non trouvée ou inactive")
            return {
                'success': False,
                'error': 'Alerte non trouvée ou inactive'
            }
        
        # Créer le service de surveillance
        monitor_service = InterfaceMonitorService(alert)
        
        # Exécuter la vérification de manière asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(monitor_service.check_interfaces())
        finally:
            loop.close()
        
        logger.info(f"Vérification terminée pour l'alerte {alert_id}: {result}")
        
        # Programmer la prochaine vérification
        schedule_next_check(alert_id)
        
        return result
        
    except Exception as e:
        error_msg = f"Erreur lors de la vérification des interfaces: {str(e)}"
        logger.error(error_msg)
        
        # Programmer la prochaine vérification malgré l'erreur
        try:
            schedule_next_check(alert_id)
        except:
            pass
        
        return {
            'success': False,
            'error': str(e)
        }


# @shared_task(name='interface_monitor.schedule_next_check')
def schedule_next_check(alert_id: str) -> bool:
    """
    Programme la prochaine vérification d'une alerte
    
    Args:
        alert_id: ID de l'alerte
        
    Returns:
        True si la planification a réussi
    """
    try:
        logger.info(f"Planification de la prochaine vérification pour l'alerte: {alert_id}")
        
        # Récupérer l'alerte
        try:
            alert = InterfaceAlert.objects.get(id=alert_id, is_active=True)
        except InterfaceAlert.DoesNotExist:
            logger.warning(f"Alerte {alert_id} non trouvée ou inactive")
            return False
        
        # Calculer la prochaine vérification
        next_check = alert.calculate_next_check()
        
        # Programmer la tâche
        # check_firewall_interfaces.apply_async(
        #     args=[alert_id],
        #     eta=next_check,
        #     expires=next_check + timezone.timedelta(hours=1)  # Expire après 1h
        # )
        
        logger.info(f"Prochaine vérification programmée pour {alert_id} à {next_check}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la planification de la prochaine vérification: {str(e)}")
        return False


# @shared_task(name='interface_monitor.check_all_active_alerts')
def check_all_active_alerts() -> Dict[str, Any]:
    """
    Vérifie toutes les alertes actives qui doivent être vérifiées maintenant
    
    Returns:
        Résumé des vérifications effectuées
    """
    try:
        logger.info("Début de la vérification de toutes les alertes actives")
        
        # Récupérer toutes les alertes actives qui doivent être vérifiées
        now = timezone.now()
        alerts_to_check = InterfaceAlert.objects.filter(
            is_active=True,
            next_check__lte=now
        ).select_related('firewall', 'firewall__firewall_type')
        
        logger.info(f"{alerts_to_check.count()} alertes à vérifier")
        
        results = []
        for alert in alerts_to_check:
            try:
                # Exécuter la vérification immédiatement (sans Celery)
                monitor_service = InterfaceMonitorService(alert)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(monitor_service.check_interfaces())
                    results.append({
                        'alert_id': str(alert.id),
                        'alert_name': alert.name,
                        'firewall': alert.firewall.name,
                        'status': 'completed' if result.get('success') else 'failed',
                        'alerts_triggered': result.get('alerts_triggered', 0)
                    })
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Erreur lors de la vérification pour {alert.name}: {str(e)}")
                results.append({
                    'alert_id': str(alert.id),
                    'alert_name': alert.name,
                    'firewall': alert.firewall.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        summary = {
            'total_alerts': len(alerts_to_check),
            'scheduled': len([r for r in results if r['status'] == 'scheduled']),
            'errors': len([r for r in results if r['status'] == 'error']),
            'results': results
        }
        
        logger.info(f"Vérification de toutes les alertes terminée: {summary}")
        return summary
        
    except Exception as e:
        error_msg = f"Erreur lors de la vérification de toutes les alertes: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e)
        }


# @shared_task(name='interface_monitor.cleanup_old_executions')
def cleanup_old_executions(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Nettoie les anciennes exécutions d'alertes
    
    Args:
        days_to_keep: Nombre de jours à conserver
        
    Returns:
        Résumé du nettoyage
    """
    try:
        logger.info(f"Nettoyage des exécutions d'alertes de plus de {days_to_keep} jours")
        
        # Calculer la date limite
        cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
        
        # Compter les exécutions à supprimer
        executions_to_delete = AlertExecution.objects.filter(
            started_at__lt=cutoff_date
        )
        
        count = executions_to_delete.count()
        
        if count > 0:
            # Supprimer les anciennes exécutions
            executions_to_delete.delete()
            logger.info(f"{count} anciennes exécutions supprimées")
        else:
            logger.info("Aucune ancienne exécution à supprimer")
        
        return {
            'success': True,
            'deleted_count': count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        error_msg = f"Erreur lors du nettoyage des anciennes exécutions: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e)
        }


def cleanup_old_status(days_to_keep: int = 14) -> Dict[str, Any]:
    """Supprime les InterfaceStatus plus anciens que N jours (rétention)."""
    try:
        logger.info(f"Nettoyage des InterfaceStatus de plus de {days_to_keep} jours")
        cutoff = timezone.now() - timezone.timedelta(days=days_to_keep)
        qs = InterfaceAlert.objects.none()  # placeholder to avoid linter; real import below
        from .models import InterfaceStatus  # local import to avoid cycles
        del_count, _ = InterfaceStatus.objects.filter(last_seen__lt=cutoff).delete()
        return {
            'success': True,
            'deleted_count': del_count,
            'cutoff_date': cutoff.isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des statuts: {str(e)}")
        return {'success': False, 'error': str(e)}


# @shared_task(name='interface_monitor.test_alert')
def test_alert(alert_id: str) -> Dict[str, Any]:
    """
    Teste une alerte en l'exécutant immédiatement
    
    Args:
        alert_id: ID de l'alerte à tester
        
    Returns:
        Résultat du test
    """
    try:
        logger.info(f"Test de l'alerte: {alert_id}")
        
        # Récupérer l'alerte
        try:
            alert = InterfaceAlert.objects.get(id=alert_id)
        except InterfaceAlert.DoesNotExist:
            return {
                'success': False,
                'error': 'Alerte non trouvée'
            }
        
        # Créer le service de surveillance
        monitor_service = InterfaceMonitorService(alert)
        
        # Exécuter la vérification de manière asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(monitor_service.check_interfaces())
        finally:
            loop.close()
        
        logger.info(f"Test de l'alerte {alert_id} terminé: {result}")
        
        return {
            'success': True,
            'test_result': result,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Erreur lors du test de l'alerte: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': str(e)
        }


# @shared_task(name='interface_monitor.health_check')
def health_check() -> Dict[str, Any]:
    """
    Vérifie la santé du système de surveillance des interfaces
    
    Returns:
        État de santé du système
    """
    try:
        logger.info("Vérification de la santé du système de surveillance")
        
        # Statistiques des alertes
        total_alerts = InterfaceAlert.objects.count()
        active_alerts = InterfaceAlert.objects.filter(is_active=True).count()
        inactive_alerts = total_alerts - active_alerts
        
        # Alertes qui doivent être vérifiées
        now = timezone.now()
        overdue_alerts = InterfaceAlert.objects.filter(
            is_active=True,
            next_check__lt=now
        ).count()
        
        # Dernières exécutions
        recent_executions = AlertExecution.objects.filter(
            started_at__gte=now - timezone.timedelta(hours=1)
        )
        
        successful_executions = recent_executions.filter(status='completed').count()
        failed_executions = recent_executions.filter(status='failed').count()
        running_executions = recent_executions.filter(status='running').count()
        
        # Calculer le taux de succès
        total_recent = successful_executions + failed_executions
        success_rate = (successful_executions / total_recent * 100) if total_recent > 0 else 0
        
        health_status = 'healthy'
        if success_rate < 80:
            health_status = 'warning'
        if success_rate < 50:
            health_status = 'critical'
        
        health_data = {
            'status': health_status,
            'timestamp': now.isoformat(),
            'alerts': {
                'total': total_alerts,
                'active': active_alerts,
                'inactive': inactive_alerts,
                'overdue': overdue_alerts
            },
            'executions': {
                'recent_total': total_recent,
                'successful': successful_executions,
                'failed': failed_executions,
                'running': running_executions,
                'success_rate': round(success_rate, 2)
            },
            'recommendations': []
        }
        
        # Ajouter des recommandations
        if overdue_alerts > 0:
            health_data['recommendations'].append(f"{overdue_alerts} alerte(s) en retard de vérification")
        
        if success_rate < 80:
            health_data['recommendations'].append("Taux de succès faible, vérifier la configuration")
        
        if failed_executions > 0:
            health_data['recommendations'].append(f"{failed_executions} exécution(s) en échec récentes")
        
        logger.info(f"Vérification de santé terminée: {health_status}")
        return health_data
        
    except Exception as e:
        error_msg = f"Erreur lors de la vérification de santé: {str(e)}"
        logger.error(error_msg)
        
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


# @shared_task(name='interface_monitor.initialize_monitoring')
def initialize_monitoring() -> Dict[str, Any]:
    """
    Initialise le système de surveillance en programmant toutes les alertes actives
    
    Returns:
        Résumé de l'initialisation
    """
    try:
        logger.info("Initialisation du système de surveillance des interfaces")
        
        # Récupérer toutes les alertes actives
        active_alerts = InterfaceAlert.objects.filter(is_active=True)
        
        scheduled_count = 0
        errors = []
        
        for alert in active_alerts:
            try:
                # Programmer la première vérification
                if schedule_next_check(str(alert.id)):
                    scheduled_count += 1
                    logger.info(f"Alerte {alert.name} programmée")
                else:
                    errors.append(f"Échec de la programmation de {alert.name}")
                    
            except Exception as e:
                error_msg = f"Erreur lors de la programmation de {alert.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Démarrer le runner en arrière-plan si non démarré
        _start_background_runner()
        
        result = {
            'success': True,
            'total_alerts': active_alerts.count(),
            'scheduled_count': scheduled_count,
            'errors': errors,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Initialisation terminée: {scheduled_count}/{active_alerts.count()} alertes programmées")
        return result
        
    except Exception as e:
        error_msg = f"Erreur lors de l'initialisation: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


def _runner_loop():
    default_interval = 60
    logger.info("Interface monitor background runner démarré")
    while True:
        try:
            # Stagger: sleep a small random jitter between alerts
            summary = check_all_active_alerts()
            # Periodic retention cleanup once per day window
            try:
                now = timezone.now()
                if now.hour == 3 and now.minute < 2:  # between 03:00 and 03:02
                    cleanup_old_status(days_to_keep=14)
                    cleanup_old_executions(days_to_keep=30)
            except Exception:
                pass
            # If nothing due, sleep longer
            total = summary.get('total_alerts', 0)
            scheduled = summary.get('scheduled', 0)
            completed = summary.get('completed', 0) if 'completed' in summary else 0
            if scheduled == 0 and completed == 0:
                time.sleep(default_interval)
            else:
                time.sleep(10)
        except Exception as e:
            logger.error(f"Erreur runner interface monitor: {str(e)}")
        


def _start_background_runner():
    global _RUNNER_STARTED
    if _RUNNER_STARTED:
        return
    try:
        thread = threading.Thread(target=_runner_loop, name="interface_monitor_runner", daemon=True)
        thread.start()
        _RUNNER_STARTED = True
        logger.info("Runner périodique des alertes d'interface initialisé")
    except Exception as e:
        logger.error(f"Impossible de démarrer le runner périodique: {str(e)}")
