"""
Commande Django pour démarrer manuellement le système de monitoring des interfaces.
"""

from django.core.management.base import BaseCommand
from interface_monitor_service.tasks import start_monitoring_system, health_check


class Command(BaseCommand):
    help = 'Démarre le système de monitoring des interfaces'

    def add_arguments(self, parser):
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Effectue un contrôle de santé du système après le démarrage',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Démarrage du système de monitoring des interfaces...')
        )
        
        try:
            # Démarrer le système de monitoring
            result = start_monitoring_system()
            
            if result.get('success'):
                self.stdout.write(
                    self.style.SUCCESS('✅ Système de monitoring démarré avec succès!')
                )
                
                # Afficher les détails de l'initialisation
                init_details = result.get('initialization', {})
                if init_details:
                    self.stdout.write(f"📊 Alertes actives: {init_details.get('total_alerts', 0)}")
                    self.stdout.write(f"📅 Alertes programmées: {init_details.get('scheduled_count', 0)}")
                    
                    if init_details.get('errors'):
                        self.stdout.write(
                            self.style.WARNING('⚠️ Erreurs lors de l\'initialisation:')
                        )
                        for error in init_details['errors']:
                            self.stdout.write(f"  - {error}")
                
                # Effectuer un contrôle de santé si demandé
                if options['health_check']:
                    self.stdout.write('\n🔍 Contrôle de santé du système...')
                    health_result = health_check()
                    
                    if health_result.get('status') == 'healthy':
                        self.stdout.write(
                            self.style.SUCCESS('✅ Système en bonne santé')
                        )
                    elif health_result.get('status') == 'warning':
                        self.stdout.write(
                            self.style.WARNING('⚠️ Système en état d\'avertissement')
                        )
                    elif health_result.get('status') == 'critical':
                        self.stdout.write(
                            self.style.ERROR('❌ Système en état critique')
                        )
                    
                    # Afficher les recommandations
                    recommendations = health_result.get('recommendations', [])
                    if recommendations:
                        self.stdout.write('\n💡 Recommandations:')
                        for rec in recommendations:
                            self.stdout.write(f"  - {rec}")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Échec du démarrage: {result.get("error")}')
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur lors du démarrage: {str(e)}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Le système de monitoring est maintenant actif!')
        )
        self.stdout.write('📧 Les emails automatiques seront envoyés toutes les 5 minutes si des alertes sont déclenchées.')
        self.stdout.write('🔄 Le système vérifie les alertes toutes les 30 secondes.')
