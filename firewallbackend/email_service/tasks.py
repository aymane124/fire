import asyncio
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from .models import AutomatedEmailSchedule, AutomatedEmailExecution
from .views import AutomatedEmailScheduleViewSet

logger = logging.getLogger(__name__)


class EmailSchedulerService:
    """Service pour gérer l'exécution automatique des emails planifiés"""
    
    def __init__(self):
        self.viewset = AutomatedEmailScheduleViewSet()
    
    async def check_and_execute_schedules(self):
        """Vérifier et exécuter les plannings d'emails qui doivent être envoyés"""
        try:
            # Récupérer tous les plannings actifs
            active_schedules = AutomatedEmailSchedule.objects.filter(is_active=True)
            
            current_time = timezone.now()
            
            for schedule in active_schedules:
                # Vérifier si c'est le moment d'envoyer
                if self.should_send_now(schedule, current_time):
                    logger.info(f"Exécution du planning: {schedule.name}")
                    await self.execute_schedule(schedule)
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des plannings: {str(e)}")
    
    def should_send_now(self, schedule, current_time):
        """Vérifier si un planning doit être exécuté maintenant"""
        # Si c'est la première fois ou si le dernier envoi était hier
        if not schedule.last_sent:
            return True
        
        # Vérifier si l'heure actuelle correspond à l'heure programmée
        schedule_time = schedule.send_time
        current_time_only = current_time.time()
        
        # Tolérance de 5 minutes
        tolerance = timezone.timedelta(minutes=5)
        
        # Vérifier si on est dans la fenêtre de temps
        if abs((current_time_only.hour * 60 + current_time_only.minute) - 
               (schedule_time.hour * 60 + schedule_time.minute)) <= 5:
            
            # Vérifier que le dernier envoi était hier ou plus ancien
            yesterday = current_time.date() - timezone.timedelta(days=1)
            return schedule.last_sent.date() <= yesterday
        
        return False
    
    async def execute_schedule(self, schedule):
        """Exécuter un planning d'email"""
        try:
            with transaction.atomic():
                # Créer l'enregistrement d'exécution
                execution = AutomatedEmailExecution.objects.create(
                    schedule=schedule,
                    status='pending'
                )
                
                # Lancer l'exécution
                await self.viewset.execute_email_schedule(execution.id)
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du planning {schedule.name}: {str(e)}")


class EmailSchedulerCommand(BaseCommand):
    """Commande Django pour exécuter le planificateur d'emails"""
    
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
    
    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
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
                    timezone.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Arrêt du planificateur'))


# Fonction utilitaire pour exécuter manuellement un planning
async def execute_schedule_manually(schedule_id):
    """Exécuter manuellement un planning d'email"""
    try:
        schedule = AutomatedEmailSchedule.objects.get(id=schedule_id)
        scheduler = EmailSchedulerService()
        await scheduler.execute_schedule(schedule)
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution manuelle: {str(e)}")
        return False


# Fonction pour vérifier les plannings en retard
def check_overdue_schedules():
    """Vérifier les plannings qui sont en retard"""
    current_time = timezone.now()
    overdue_schedules = []
    
    for schedule in AutomatedEmailSchedule.objects.filter(is_active=True):
        if schedule.next_send and schedule.next_send < current_time:
            overdue_schedules.append(schedule)
    
    return overdue_schedules


# Fonction pour reprogrammer les plannings en retard
def reschedule_overdue_schedules():
    """Reprogrammer les plannings qui sont en retard"""
    overdue_schedules = check_overdue_schedules()
    
    for schedule in overdue_schedules:
        schedule.next_send = schedule.calculate_next_send()
        schedule.save()
        logger.info(f"Planning reprogrammé: {schedule.name} -> {schedule.next_send}")
    
    return len(overdue_schedules)
