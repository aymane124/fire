from django.apps import AppConfig


class InterfaceMonitorServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interface_monitor_service'
    verbose_name = 'Interface Monitor Service'
    
    def ready(self):
        """Initialisation du service lors du démarrage"""
        try:
            # Importer les signaux et tâches
            import interface_monitor_service.signals
            import interface_monitor_service.tasks
        except ImportError:
            pass
