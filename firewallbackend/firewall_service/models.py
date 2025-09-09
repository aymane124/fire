from django.db import models
from django.utils import timezone
import uuid
import json
from auth_service.models import User
from datacenter_service.models import DataCenter
from history_service.models import ServiceHistory


class FirewallType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    attributes_schema = models.JSONField()
    data_center = models.ForeignKey(DataCenter, on_delete=models.CASCADE, related_name='firewall_types')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='firewall_types')
    created_at = models.DateTimeField(default=timezone.now)
    historique_firewall = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'firewall_type'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['data_center']),
            models.Index(fields=['owner']),
        ]
        unique_together = ['name', 'data_center']

    def __str__(self):
        return f"{self.name} ({self.data_center.name})"

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_firewall:
            self.historique_firewall = {'entries': []}
        
        self.historique_firewall['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='firewall_type',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

class Firewall(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    data_center = models.ForeignKey(DataCenter, on_delete=models.CASCADE, related_name='firewalls', null=True)
    firewall_type = models.ForeignKey(FirewallType, on_delete=models.CASCADE, related_name='firewalls')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='firewalls')
    ssh_user = models.CharField(max_length=50, default='admin', help_text='Nom d\'utilisateur SSH')
    ssh_password = models.CharField(max_length=255, blank=True, help_text='Mot de passe SSH (optionnel)')
    ssh_port = models.IntegerField(default=22, help_text='Port SSH')
    created_at = models.DateTimeField(default=timezone.now)
    historique_firewall = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'firewall'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['data_center']),
            models.Index(fields=['firewall_type']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_firewall:
            self.historique_firewall = {'entries': []}
        
        self.historique_firewall['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='firewall',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

