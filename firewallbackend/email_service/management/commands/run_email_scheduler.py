from django.core.management.base import BaseCommand
from django.utils import timezone
import asyncio
import time
from email_service.tasks import EmailSchedulerService

class Command(BaseCommand):
    help = 'Exécute le planificateur d\'emails automatiques'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Intervalle de vérification en secondes (défaut: 60)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Exécuter une seule fois et quitter'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Exécuter en mode daemon (en arrière-plan)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        daemon_mode = options['daemon']

        if daemon_mode:
            self.stdout.write(
                self.style.SUCCESS(f'Démarrage du planificateur d\'emails en mode daemon (intervalle: {interval}s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Démarrage du planificateur d\'emails (intervalle: {interval}s)')
            )

        scheduler = EmailSchedulerService()

        if run_once:
            # Exécution unique
            asyncio.run(scheduler.check_and_execute_schedules())
            self.stdout.write(self.style.SUCCESS('Exécution terminée'))
        else:
            # Exécution continue
            try:
                while True:
                    asyncio.run(scheduler.check_and_execute_schedules())
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Arrêt du planificateur'))
