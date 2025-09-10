from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import json

User = get_user_model()


class InterfaceAlert(models.Model):
    """Modèle pour configurer les alertes de surveillance des interfaces"""
    
    ALERT_TYPES = [
        ('interface_down', 'Interface Down'),
        ('interface_up', 'Interface Up'),
        ('bandwidth_high', 'Bande passante élevée'),
        ('error_count', 'Compteur d\'erreurs'),
        ('custom', 'Personnalisé')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nom de l'alerte")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Configuration de l'alerte
    firewall = models.ForeignKey(
        'firewall_service.Firewall',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Firewall (optionnel)"
    )
    # Informations complémentaires sur le type et la portée
    firewall_type = models.CharField(
        max_length=100,
        blank=True,
        help_text='Type de firewall (ex: FortiGate, Cisco, etc.)'
    )
    firewalls = models.ManyToManyField(
        'firewall_service.Firewall',
        related_name='interface_alerts',
        verbose_name='Firewalls',
        blank=True
    )
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, verbose_name="Type d'alerte")
    
    # Paramètres de surveillance
    check_interval = models.IntegerField(default=360, help_text="Intervalle en secondes (forcé à 6 min)" )
    threshold_value = models.FloatField(null=True, blank=True, help_text="Valeur seuil pour les alertes numériques")
    command_template = models.TextField(default="show system interface", help_text="Commande à exécuter")
    
    # Configuration des conditions
    conditions = models.JSONField(default=dict, help_text="Conditions personnalisées pour l'alerte")
    
    # Destinataires
    recipients = models.ManyToManyField(User, verbose_name="Destinataires")
    include_admin = models.BooleanField(default=True, verbose_name="Inclure les admins")
    include_superuser = models.BooleanField(default=True, verbose_name="Inclure les superusers")
    
    # Statut et activation
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    last_check = models.DateTimeField(null=True, blank=True, verbose_name="Dernière vérification")
    last_status = models.CharField(max_length=20, default='unknown', verbose_name="Dernier statut")
    next_check = models.DateTimeField(null=True, blank=True, verbose_name="Prochaine vérification")
    
    # Métadonnées
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_interface_alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'interface_alert'
        verbose_name = 'Alerte Interface'
        verbose_name_plural = 'Alertes Interfaces'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['firewall']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['next_check']),
        ]

    def __str__(self):
        return f"{self.name} - {self.firewall.name}"

    def get_recipients(self):
        """Retourne la liste complète des destinataires"""
        recipients = list(self.recipients.all())
        
        if self.include_admin:
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            recipients.extend(admin_users)
        
        if self.include_superuser:
            superusers = User.objects.filter(is_superuser=True, is_active=True)
            recipients.extend(superusers)
        
        # Supprimer les doublons
        return list(set(recipients))

    def calculate_next_check(self):
        """Calcule la prochaine date de vérification"""
        # Toujours calculer à partir de maintenant pour éviter les problèmes de temps
        now = timezone.now()
        next_check = now + timezone.timedelta(seconds=self.check_interval)
        
        self.next_check = next_check
        self.save(update_fields=['next_check'])
        return next_check

    def should_check_now(self):
        """Vérifie si l'alerte doit être vérifiée maintenant"""
        if not self.is_active:
            return False
        
        if not self.next_check:
            return True
        
        return timezone.now() >= self.next_check


class InterfaceStatus(models.Model):
    """Modèle pour tracer l'état des interfaces"""
    
    STATUS_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
        ('error', 'Error'),
        ('unknown', 'Unknown'),
        ('disabled', 'Disabled')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(InterfaceAlert, on_delete=models.CASCADE, related_name='status_checks')
    interface_name = models.CharField(max_length=100, verbose_name="Nom de l'interface")
    
    # Statut de l'interface
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Statut")
    
    # Métriques de performance
    bandwidth_in = models.FloatField(null=True, blank=True, help_text="Bande passante entrante (Mbps)")
    bandwidth_out = models.FloatField(null=True, blank=True, help_text="Bande passante sortante (Mbps)")
    error_count = models.IntegerField(default=0, help_text="Nombre d'erreurs")
    packet_loss = models.FloatField(null=True, blank=True, help_text="Perte de paquets (%)")
    
    # Informations de connexion
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    mac_address = models.CharField(max_length=17, blank=True, verbose_name="Adresse MAC")
    
    # Données brutes et timestamp
    raw_output = models.TextField(blank=True, help_text="Sortie brute de la commande")
    last_seen = models.DateTimeField(auto_now_add=True, verbose_name="Dernière observation")
    
    class Meta:
        db_table = 'interface_status'
        verbose_name = 'Statut Interface'
        verbose_name_plural = 'Statuts Interfaces'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['alert']),
            models.Index(fields=['interface_name']),
            models.Index(fields=['status']),
            models.Index(fields=['last_seen']),
            models.Index(fields=['alert', 'status', 'last_seen'], name='idx_alert_status_seen'),
        ]

    def __str__(self):
        return f"{self.interface_name} - {self.status} ({self.alert.name})"


class AlertExecution(models.Model):
    """Modèle pour tracer l'exécution des alertes"""
    
    EXECUTION_STATUS = [
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(InterfaceAlert, on_delete=models.CASCADE, related_name='executions')
    
    # Statut d'exécution
    status = models.CharField(max_length=20, choices=EXECUTION_STATUS, default='pending')
    
    # Informations d'exécution
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text="Durée en secondes")
    
    # Résultats
    interfaces_checked = models.IntegerField(default=0)
    alerts_triggered = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    
    # Détails et erreurs
    details = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'alert_execution'
        verbose_name = 'Exécution d\'Alerte'
        verbose_name_plural = 'Exécutions d\'Alertes'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['alert']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"{self.alert.name} - {self.status} ({self.started_at})"

    def mark_completed(self, details=None):
        """Marque l'exécution comme terminée"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.duration = (self.completed_at - self.started_at).total_seconds()
        
        if details:
            self.details = details
        
        self.save()

    def mark_failed(self, error_message, details=None):
        """Marque l'exécution comme échouée"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.duration = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        
        if details:
            self.details = details
        
        self.save()
