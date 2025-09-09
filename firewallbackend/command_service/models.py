from django.db import models
from django.conf import settings
from auth_service.models import User
from firewall_service.models import Firewall
from auth_service.utils.crypto import decrypt_ssh_data
import logging
from datetime import datetime
import json
from django.utils import timezone
from history_service.models import ServiceHistory

logger = logging.getLogger(__name__)

class FirewallCommand(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('executing', 'Executing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    firewall = models.ForeignKey(Firewall, on_delete=models.CASCADE, related_name='commands')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    command = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    output = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historique_command = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Command {self.id} for {self.firewall.name}"

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address,
            'firewall_info': {
                'id': str(self.firewall.id),
                'name': self.firewall.name,
                'ip_address': self.firewall.ip_address,
                'type': self.firewall.firewall_type.name if self.firewall.firewall_type else None,
                'data_center': self.firewall.data_center.name if self.firewall.data_center else None
            },
            'command_info': {
                'raw_command': self.command,
                'status': self.status,
                'output_length': len(self.output) if self.output else 0,
                'has_error': bool(self.error_message),
                'error_message': self.error_message
            }
        }
        
        if not self.historique_command:
            self.historique_command = {'entries': []}
        
        self.historique_command['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='command',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

    def execute(self, ssh_username, ssh_password):
        """
        Exécute la commande sur le pare-feu via SSH
        """
        try:
            # Déchiffrer le mot de passe SSH si nécessaire
            if isinstance(ssh_password, bytes):
                ssh_password = decrypt_ssh_data(ssh_password.decode('utf-8'))
            elif isinstance(ssh_password, str):
                ssh_password = decrypt_ssh_data(ssh_password)

            # Implémenter la logique d'exécution SSH ici
            # Cette méthode devrait être implémentée selon vos besoins spécifiques
            return "Command executed successfully"
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            raise
