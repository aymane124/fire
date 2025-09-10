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
        
        # Construire la liste des firewalls cibles
        from firewall_service.models import Firewall
        targets = []
        if alert.firewall:
            targets.append(alert.firewall)
        # M2M explicites
        try:
            targets.extend(list(alert.firewalls.all()))
        except Exception:
            pass
        # Par type (optionnel): rechercher par nom de type case-insensitive
        fw_type = (alert.firewall_type or '').strip()
        if fw_type:
            qs = Firewall.objects.all()
            # Essayer de résoudre par relation si le modèle a firewall_type.name
            try:
                targets.extend(list(qs.filter(firewall_type__name__iexact=fw_type)))
            except Exception:
                # Fallback: si firewall.firewall_type est un simple champ texte
                try:
                    targets.extend(list(qs.filter(firewall_type__iexact=fw_type)))
                except Exception:
                    pass
        # Scope filtering by owner
        try:
            targets = [fw for fw in targets if getattr(fw, 'owner_id', None) == alert.created_by_id]
        except Exception:
            pass
        # Dédupliquer par id
        uniq = {}
        for fw in targets:
            uniq[str(getattr(fw, 'id', fw))] = fw
        target_firewalls = list(uniq.values())

        if not target_firewalls:
            logger.warning(f"Aucune cible trouvée pour l'alerte {alert_id}")
            return {'success': False, 'error': 'Aucune cible'}

        results_agg = {
            'success': True,
            'targets': [],
            'interfaces_checked': 0,
            'alerts_triggered': 0,
            'emails_sent': 0,
        }
        # Pour agrégation email
        aggregate_interfaces: list = []
        aggregate_alerts_triggered: list = []

        # Exécuter séquentiellement sur chaque firewall cible
        for fw in target_firewalls:
            try:
                # Instancier un service par cible
                monitor_service = InterfaceMonitorService(alert)
                # Remplacer la cible courante
                monitor_service.firewall = fw
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(monitor_service.check_interfaces())
                finally:
                    loop.close()
                results_agg['targets'].append({
                    'firewall': getattr(fw, 'name', str(getattr(fw, 'id', 'unknown'))),
                    'result': result
                })
                if result.get('success'):
                    results_agg['interfaces_checked'] += int(result.get('interfaces_checked', 0))
                    results_agg['alerts_triggered'] += int(result.get('alerts_triggered', 0))
                    results_agg['emails_sent'] += int(result.get('emails_sent', 0))
                    # Agréger pour email unique si demandé
                    try:
                        if (alert.conditions or {}).get('aggregate_email'):
                            aggregate_interfaces.extend(result.get('interfaces') or [])
                            # Reconstruire alerts_triggered minimal depuis interfaces DOWN
                            down = [i for i in (result.get('interfaces') or []) if i.get('status') == 'down']
                            for di in down:
                                aggregate_alerts_triggered.append({'interface': di, 'reason': 'Interface down', 'alert_type': alert.alert_type})
                    except Exception:
                        pass
                else:
                    results_agg['success'] = False
            except Exception as e:
                logger.error(f"Erreur exécution cible {getattr(fw, 'name', 'unknown')}: {str(e)}")
                results_agg['targets'].append({
                    'firewall': getattr(fw, 'name', str(getattr(fw, 'id', 'unknown'))),
                    'error': str(e)
                })
                results_agg['success'] = False

        # Si agrégation demandée, envoyer un seul email récapitulatif
        try:
            if (alert.conditions or {}).get('aggregate_email'):
                from .alert_service import AlertEmailService
                email_service = AlertEmailService(alert)
                recipients = alert.get_recipients()
                _ = asyncio.new_event_loop()
                # Utiliser une boucle courte pour appeler la coroutine d'envoi
                loop = _
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(email_service.send_interface_alert(aggregate_interfaces, aggregate_alerts_triggered, recipients=recipients))
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"Erreur envoi email agrégé: {str(e)}")

        logger.info(f"Vérification terminée pour l'alerte {alert_id}: {results_agg}")
        # La prochaine vérification est déjà programmée dans services.py
        return results_agg
        
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
        
        logger.info(f"Vérification à {now}: {alerts_to_check.count()} alertes à vérifier")
        
        # Log des détails pour le débogage
        for alert in alerts_to_check:
            logger.info(f"  - {alert.name}: next_check={alert.next_check}, last_check={alert.last_check}")
        
        results = []
        for alert in alerts_to_check:
            try:
                # Exécuter la vérification immédiatement (sans Celery)
                # Résolution dynamique des cibles (single/M2M/type)
                from firewall_service.models import Firewall
                targets = []
                if alert.firewall:
                    targets.append(alert.firewall)
                try:
                    targets.extend(list(alert.firewalls.all()))
                except Exception:
                    pass
                fw_type = (alert.firewall_type or '').strip()
                if fw_type:
                    try:
                        targets.extend(list(Firewall.objects.filter(firewall_type__name__iexact=fw_type)))
                    except Exception:
                        try:
                            targets.extend(list(Firewall.objects.filter(firewall_type__iexact=fw_type)))
                        except Exception:
                            pass
                # Scope filtering by owner
                try:
                    targets = [fw for fw in targets if getattr(fw, 'owner_id', None) == alert.created_by_id]
                except Exception:
                    pass
                # Dédupliquer
                uniq = {}
                for fw in targets:
                    uniq[str(getattr(fw, 'id', fw))] = fw
                target_firewalls = list(uniq.values())

                if not target_firewalls:
                    logger.warning(f"Aucune cible pour {alert.name}")
                    continue

                for fw in target_firewalls:
                    monitor_service = InterfaceMonitorService(alert)
                    monitor_service.firewall = fw
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(monitor_service.check_interfaces())
                        results.append({
                            'alert_id': str(alert.id),
                            'alert_name': alert.name,
                            'firewall': getattr(fw, 'name', 'unknown'),
                            'status': 'completed' if result.get('success') else 'failed',
                            'alerts_triggered': result.get('alerts_triggered', 0),
                            'emails_sent': result.get('emails_sent', 0)
                        })
                        # Agréger si demandé
                        try:
                            if (alert.conditions or {}).get('aggregate_email'):
                                from .alert_service import AlertEmailService
                                # Accumuler dans un buffer par alerte (simplifié ici: ignorer et laisser check_firewall_interfaces gérer)
                                pass
                        except Exception:
                            pass
                    finally:
                        loop.close()
            except Exception as e:
                logger.error(f"Erreur lors de la vérification pour {alert.name}: {str(e)}")
                
                # Programmer la prochaine vérification en cas d'erreur
                try:
                    schedule_next_check(str(alert.id))
                except:
                    pass
                
                results.append({
                    'alert_id': str(alert.id),
                    'alert_name': alert.name,
                    'firewall': getattr(getattr(alert, 'firewall', None), 'name', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
        
        summary = {
            'total_alerts': len(alerts_to_check),
            'completed': len([r for r in results if r['status'] == 'completed']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'errors': len([r for r in results if r['status'] == 'error']),
            'total_emails_sent': sum([r.get('emails_sent', 0) for r in results]),
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
        
        # Résoudre les cibles (single/M2M/type)
        from firewall_service.models import Firewall
        targets = []
        if alert.firewall:
            targets.append(alert.firewall)
        try:
            targets.extend(list(alert.firewalls.all()))
        except Exception:
            pass
        fw_type = (alert.firewall_type or '').strip()
        if fw_type:
            try:
                targets.extend(list(Firewall.objects.filter(firewall_type__name__iexact=fw_type)))
            except Exception:
                try:
                    targets.extend(list(Firewall.objects.filter(firewall_type__iexact=fw_type)))
                except Exception:
                    pass
        uniq = {}
        for fw in targets:
            uniq[str(getattr(fw, 'id', fw))] = fw
        target_firewalls = list(uniq.values())

        if not target_firewalls:
            return {'success': False, 'error': 'Aucune cible trouvée', 'timestamp': timezone.now().isoformat()}

        aggregated = {
            'success': True,
            'targets': [],
            'timestamp': timezone.now().isoformat()
        }

        for fw in target_firewalls:
            monitor_service = InterfaceMonitorService(alert)
            monitor_service.firewall = fw
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(monitor_service.check_interfaces())
                aggregated['targets'].append({
                    'firewall': getattr(fw, 'name', 'unknown'),
                    'result': result
                })
                if not result.get('success'):
                    aggregated['success'] = False
            finally:
                loop.close()

        logger.info(f"Test de l'alerte {alert_id} terminé: {aggregated}")
        return aggregated
        
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
    default_interval = 360  # Vérifier toutes les 6 minutes
    logger.info("Interface monitor background runner démarré")
    while True:
        try:
            # Vérifier toutes les alertes actives qui doivent être vérifiées
            summary = check_all_active_alerts()
            
            # Periodic retention cleanup once per day window
            try:
                now = timezone.now()
                if now.hour == 3 and now.minute < 2:  # between 03:00 and 03:02
                    cleanup_old_status(days_to_keep=14)
                    cleanup_old_executions(days_to_keep=30)
            except Exception:
                pass
            
            # Toujours dormir 30 secondes pour une vérification régulière
            time.sleep(default_interval)
            
        except Exception as e:
            logger.error(f"Erreur runner interface monitor: {str(e)}")
            # En cas d'erreur, attendre plus longtemps avant de réessayer
            time.sleep(60)
        


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


def start_monitoring_system():
    """
    Démarre le système de monitoring des interfaces.
    Cette fonction doit être appelée au démarrage de l'application.
    """
    try:
        logger.info("Démarrage du système de monitoring des interfaces")
        
        # Initialiser le monitoring
        init_result = initialize_monitoring()
        logger.info(f"Initialisation du monitoring: {init_result}")
        
        # Démarrer le runner en arrière-plan
        _start_background_runner()
        
        return {
            'success': True,
            'message': 'Système de monitoring démarré avec succès',
            'initialization': init_result
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du système de monitoring: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
