import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import InterfaceAlert, AlertExecution
from .tasks import schedule_next_check, initialize_monitoring

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InterfaceAlert)
def handle_alert_save(sender, instance, created, **kwargs):
    """
    Gère la sauvegarde d'une alerte d'interface
    
    Args:
        sender: Modèle qui a déclenché le signal
        instance: Instance de l'alerte sauvegardée
        created: True si c'est une nouvelle alerte
    """
    try:
        if created:
            logger.info(f"Nouvelle alerte créée: {instance.name}")
            
            # Si l'alerte est active, programmer la première vérification
            if instance.is_active:
                # Programmer la vérification immédiatement (appel direct)
                schedule_next_check(str(instance.id))
                logger.info(f"Première vérification programmée pour l'alerte: {instance.name}")
        
        else:
            logger.info(f"Alerte modifiée: {instance.name}")
            
            # Si l'alerte est devenue active, programmer la vérification
            if instance.is_active:
                # Vérifier si une vérification est déjà programmée
                if not instance.next_check or instance.next_check <= timezone.now():
                    schedule_next_check(str(instance.id))
                    logger.info(f"Vérification reprogrammée pour l'alerte: {instance.name}")
            
            # Si l'alerte est devenue inactive, annuler les vérifications futures
            # (Celery gère automatiquement l'expiration des tâches)
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement du signal de sauvegarde: {str(e)}")


@receiver(post_delete, sender=InterfaceAlert)
def handle_alert_delete(sender, instance, **kwargs):
    """
    Gère la suppression d'une alerte d'interface
    
    Args:
        sender: Modèle qui a déclenché le signal
        instance: Instance de l'alerte supprimée
    """
    try:
        logger.info(f"Alerte supprimée: {instance.name}")
        
        # Note: Les tâches Celery en cours continueront de s'exécuter
        # mais échoueront car l'alerte n'existe plus
        # Celery gère automatiquement le nettoyage des tâches expirées
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du signal de suppression: {str(e)}")


@receiver(post_save, sender=AlertExecution)
def handle_execution_save(sender, instance, created, **kwargs):
    """
    Gère la sauvegarde d'une exécution d'alerte
    
    Args:
        sender: Modèle qui a déclenché le signal
        instance: Instance de l'exécution sauvegardée
        created: True si c'est une nouvelle exécution
    """
    try:
        if created:
            logger.info(f"Nouvelle exécution créée pour l'alerte: {instance.alert.name}")
        
        # Si l'exécution est terminée (succès ou échec), mettre à jour l'alerte
        if instance.status in ['completed', 'failed'] and instance.completed_at:
            alert = instance.alert
            
            # Mettre à jour le statut de l'alerte
            if instance.status == 'completed':
                # Extraire le statut global des détails
                details = instance.details or {}
                interfaces_status = details.get('interfaces_status', {})
                
                if interfaces_status:
                    # Déterminer le statut global
                    if any(status == 'down' for status in interfaces_status.values()):
                        global_status = 'down'
                    elif all(status == 'up' for status in interfaces_status.values()):
                        global_status = 'up'
                    else:
                        global_status = 'mixed'
                    
                    alert.last_status = global_status
                    alert.save(update_fields=['last_status'])
                    
                    logger.info(f"Statut de l'alerte {alert.name} mis à jour: {global_status}")
            
            # Programmer la prochaine vérification si l'alerte est toujours active
            if alert.is_active:
                schedule_next_check(str(alert.id))
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement du signal d'exécution: {str(e)}")


# Signal pour initialiser le système au démarrage
@receiver(post_save, sender=InterfaceAlert)
def initialize_monitoring_on_startup(sender, instance, created, **kwargs):
    """
    Initialise le système de surveillance au démarrage si c'est la première alerte
    """
    try:
        # Vérifier si c'est la première alerte active
        if created and instance.is_active:
            active_alerts_count = InterfaceAlert.objects.filter(is_active=True).count()
            
            if active_alerts_count == 1:
                logger.info("Première alerte active détectée, initialisation du système de surveillance")
                
                # Lancer l'initialisation (appel direct)
                initialize_monitoring()
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation au démarrage: {str(e)}")


# Signal pour la gestion des erreurs de connexion
def handle_connection_error(alert_id: str, error_message: str):
    """
    Gère les erreurs de connexion aux firewalls
    
    Args:
        alert_id: ID de l'alerte
        error_message: Message d'erreur
    """
    try:
        logger.error(f"Erreur de connexion pour l'alerte {alert_id}: {error_message}")
        
        # Récupérer l'alerte
        try:
            alert = InterfaceAlert.objects.get(id=alert_id)
        except InterfaceAlert.DoesNotExist:
            logger.warning(f"Alerte {alert_id} non trouvée")
            return
        
        # Créer une exécution d'erreur
        execution = AlertExecution.objects.create(
            alert=alert,
            status='failed',
            error_message=error_message,
            details={
                'error_type': 'connection_error',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Programmer une nouvelle tentative
        schedule_next_check.delay(str(alert_id))
        
        logger.info(f"Exécution d'erreur créée et nouvelle tentative programmée pour {alert_id}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la gestion de l'erreur de connexion: {str(e)}")


# Signal pour la gestion des alertes critiques
def handle_critical_alert(alert_id: str, interface_name: str, status: str):
    """
    Gère les alertes critiques (interfaces down)
    
    Args:
        alert_id: ID de l'alerte
        interface_name: Nom de l'interface
        status: Statut de l'interface
    """
    try:
        logger.warning(f"Alerte critique détectée: {interface_name} est {status} pour l'alerte {alert_id}")
        
        # Ici, vous pouvez ajouter des actions supplémentaires pour les alertes critiques
        # Par exemple:
        # - Envoyer des SMS
        # - Créer des tickets dans un système de ticketing
        # - Déclencher des actions automatiques
        # - Notifier des équipes spécifiques
        
        # Pour l'instant, on se contente de logger l'événement
        
    except Exception as e:
        logger.error(f"Erreur lors de la gestion de l'alerte critique: {str(e)}")


# Signal pour la gestion des récupérations
def handle_recovery(alert_id: str, interface_name: str, previous_status: str, new_status: str):
    """
    Gère la récupération d'une interface
    
    Args:
        alert_id: ID de l'alerte
        interface_name: Nom de l'interface
        previous_status: Statut précédent
        new_status: Nouveau statut
    """
    try:
        if previous_status in ['down', 'error'] and new_status == 'up':
            logger.info(f"Récupération détectée: {interface_name} est passé de {previous_status} à {new_status}")
            
            # Ici, vous pouvez ajouter des actions pour les récupérations
            # Par exemple:
            # - Envoyer une notification de récupération
            # - Mettre à jour des tableaux de bord
            # - Créer des rapports de disponibilité
            
    except Exception as e:
        logger.error(f"Erreur lors de la gestion de la récupération: {str(e)}")


# Configuration des signaux
def setup_signals():
    """Configure tous les signaux du service de surveillance des interfaces"""
    try:
        logger.info("Configuration des signaux du service de surveillance des interfaces")
        
        # Les signaux sont automatiquement connectés grâce aux décorateurs @receiver
        # Cette fonction peut être utilisée pour une configuration supplémentaire si nécessaire
        
        logger.info("Signaux configurés avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la configuration des signaux: {str(e)}")


# Nettoyage des signaux
def cleanup_signals():
    """Nettoie les connexions de signaux"""
    try:
        logger.info("Nettoyage des signaux du service de surveillance des interfaces")
        
        # Django gère automatiquement le nettoyage des signaux
        # Cette fonction peut être utilisée pour un nettoyage manuel si nécessaire
        
        logger.info("Signaux nettoyés avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des signaux: {str(e)}")
