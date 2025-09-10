"""
Module d'initialisation du système de monitoring des interfaces.
Ce module doit être importé au démarrage de l'application Django.
"""

import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class InterfaceMonitorConfig(AppConfig):
    """Configuration de l'application Interface Monitor"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interface_monitor_service'
    verbose_name = 'Interface Monitor Service'
    
    def ready(self):
        """Appelé quand l'application Django est prête"""
        try:
            # Éviter de démarrer le monitoring pendant les migrations
            import sys
            if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
                return
            
            # Démarrer le système de monitoring
            self._start_monitoring_system()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du monitoring: {str(e)}")
    
    def _start_monitoring_system(self):
        """Démarre le système de monitoring en arrière-plan"""
        try:
            # Importer ici pour éviter les imports circulaires
            from .tasks import start_monitoring_system
            
            # Démarrer le système de monitoring
            result = start_monitoring_system()
            
            if result.get('success'):
                logger.info("✅ Système de monitoring des interfaces démarré avec succès")
            else:
                logger.error(f"❌ Échec du démarrage du système de monitoring: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du système de monitoring: {str(e)}")


# Fonction utilitaire pour démarrer manuellement le monitoring
def start_interface_monitoring():
    """
    Fonction utilitaire pour démarrer manuellement le système de monitoring.
    Peut être appelée depuis une commande Django ou un script.
    """
    try:
        from .tasks import start_monitoring_system
        return start_monitoring_system()
    except Exception as e:
        logger.error(f"Erreur lors du démarrage manuel du monitoring: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
