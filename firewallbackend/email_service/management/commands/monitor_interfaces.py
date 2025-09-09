#!/usr/bin/env python
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from email_service.interface_monitor import run_interface_monitoring

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Commande Django pour exécuter la surveillance des interfaces firewall"""
    
    help = 'Surveille les interfaces des firewalls et envoie des alertes par email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Intervalle de vérification en minutes (défaut: 30)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Exécuter une seule fois et quitter'
        )
        parser.add_argument(
            '--alert-id',
            type=str,
            help='Vérifier une alerte spécifique par son ID'
        )
    
    def handle(self, *args, **options):
        interval_minutes = options['interval']
        run_once = options['once']
        alert_id = options['alert_id']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Démarrage de la surveillance des interfaces (intervalle: {interval_minutes}min)'
            )
        )
        
        if alert_id:
            # Vérifier une alerte spécifique
            self._check_specific_alert(alert_id)
        elif run_once:
            # Exécution unique
            self._run_once()
        else:
            # Exécution continue
            self._run_continuous(interval_minutes)
    
    def _check_specific_alert(self, alert_id):
        """Vérifier une alerte spécifique"""
        try:
            from email_service.interface_monitor import check_alert_manually
            from email_service.models import FirewallInterfaceAlert
            
            # Vérifier que l'alerte existe
            alert = FirewallInterfaceAlert.objects.get(id=alert_id)
            self.stdout.write(f'Vérification de l\'alerte: {alert.name}')
            
            # Exécuter la vérification
            success = asyncio.run(check_alert_manually(alert_id))
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('Vérification terminée avec succès')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Erreur lors de la vérification')
                )
                
        except FirewallInterfaceAlert.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Alerte {alert_id} non trouvée')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur: {str(e)}')
            )
    
    def _run_once(self):
        """Exécuter une seule vérification"""
        try:
            asyncio.run(run_interface_monitoring())
            self.stdout.write(
                self.style.SUCCESS('Vérification terminée')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la vérification: {str(e)}')
            )
    
    def _run_continuous(self, interval_minutes):
        """Exécuter la surveillance en continu"""
        import time
        
        try:
            while True:
                self.stdout.write(
                    f'[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                    f'Exécution de la surveillance...'
                )
                
                try:
                    asyncio.run(run_interface_monitoring())
                    self.stdout.write(
                        self.style.SUCCESS('Vérification terminée avec succès')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erreur lors de la vérification: {str(e)}')
                    )
                
                # Attendre avant la prochaine vérification
                self.stdout.write(
                    f'Prochaine vérification dans {interval_minutes} minutes...'
                )
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Arrêt de la surveillance')
            )
