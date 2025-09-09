from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time
import uuid

User = get_user_model()

class EmailLog(models.Model):
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    from_email = models.CharField(max_length=255, blank=True, null=True)
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, default='sent', choices=[
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending')
    ])
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'email_log'
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.recipient} - {self.subject} - {self.sent_at}"


class AutomatedEmailSchedule(models.Model):
    """Modèle pour planifier l'envoi automatique d'emails quotidiens"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nom du planning")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Configuration de l'heure d'envoi
    send_time = models.TimeField(default=time(9, 0), verbose_name="Heure d'envoi")
    timezone = models.CharField(max_length=50, default='UTC', verbose_name="Fuseau horaire")
    
    # Configuration des destinataires
    recipients = models.ManyToManyField(User, verbose_name="Destinataires")
    include_all_users = models.BooleanField(default=False, verbose_name="Inclure tous les utilisateurs")
    
    # Configuration du contenu
    email_subject = models.CharField(max_length=255, verbose_name="Sujet de l'email")
    email_template = models.TextField(verbose_name="Template de l'email")
    
    # Configuration des firewalls et commandes
    firewalls = models.ManyToManyField('firewall_service.Firewall', verbose_name="Pare-feu à vérifier")
    commands_to_execute = models.JSONField(default=list, verbose_name="Commandes à exécuter")
    
    # Statut et activation
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    last_sent = models.DateTimeField(null=True, blank=True, verbose_name="Dernier envoi")
    next_send = models.DateTimeField(null=True, blank=True, verbose_name="Prochain envoi")
    
    # Métadonnées
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'automated_email_schedule'
        verbose_name = 'Planning Email Automatique'
        verbose_name_plural = 'Plannings Emails Automatiques'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.send_time}"

    def get_recipients(self):
        """Retourne la liste des destinataires"""
        if self.include_all_users:
            return User.objects.filter(is_active=True)
        return self.recipients.filter(is_active=True)

    def calculate_next_send(self):
        """Calcule la prochaine date d'envoi"""
        now = timezone.now()
        today = now.date()
        send_datetime = timezone.make_aware(
            timezone.datetime.combine(today, self.send_time)
        )
        
        if send_datetime <= now:
            # Si l'heure est déjà passée aujourd'hui, programmer pour demain
            tomorrow = today + timezone.timedelta(days=1)
            send_datetime = timezone.make_aware(
                timezone.datetime.combine(tomorrow, self.send_time)
            )
        
        return send_datetime


class AutomatedEmailExecution(models.Model):
    """Modèle pour tracer les exécutions des emails automatiques"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(AutomatedEmailSchedule, on_delete=models.CASCADE, related_name='executions')
    
    # Informations d'exécution
    execution_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé')
    ], default='pending')
    
    # Résultats
    emails_sent = models.IntegerField(default=0)
    emails_failed = models.IntegerField(default=0)
    commands_executed = models.IntegerField(default=0)
    commands_failed = models.IntegerField(default=0)
    
    # Détails
    error_message = models.TextField(blank=True, null=True)
    execution_log = models.JSONField(default=dict)
    
    # Métadonnées
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'automated_email_execution'
        verbose_name = 'Exécution Email Automatique'
        verbose_name_plural = 'Exécutions Emails Automatiques'
        ordering = ['-execution_time']

    def __str__(self):
        return f"{self.schedule.name} - {self.execution_time} - {self.status}"


class CommandExecutionResult(models.Model):
    """Modèle pour stocker les résultats d'exécution des commandes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(AutomatedEmailExecution, on_delete=models.CASCADE, related_name='command_results')
    firewall = models.ForeignKey('firewall_service.Firewall', on_delete=models.CASCADE)
    
    # Informations de la commande
    command = models.TextField()
    command_type = models.CharField(max_length=50, blank=True)
    
    # Résultats
    status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('executing', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
        ('timeout', 'Timeout')
    ], default='pending')
    
    # Sortie de la commande
    output = models.TextField(blank=True, null=True)
    error_output = models.TextField(blank=True, null=True)
    exit_code = models.IntegerField(null=True, blank=True)
    
    # Métadonnées
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # WebSocket session info
    websocket_session_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'command_execution_result'
        verbose_name = 'Résultat Exécution Commande'
        verbose_name_plural = 'Résultats Exécution Commandes'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.firewall.name} - {self.command[:50]}... - {self.status}"



class CommandTemplate(models.Model):
    """Modèle pour stocker des modèles de commandes réutilisables"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='command_templates')
    command = models.TextField()
    command_type = models.CharField(max_length=50, default='general')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'command_template'
        verbose_name = 'Modèle de commande'
        verbose_name_plural = 'Modèles de commandes'
        ordering = ['-created_at']
        unique_together = (('owner', 'command', 'command_type'),)

    def __str__(self):
        return f"{self.command_type} - {self.command[:40]}..."

