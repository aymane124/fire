from django.db import models
from django.utils import timezone
import uuid
from auth_service.models import User
from history_service.models import ServiceHistory

class DataCenter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datacenters')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    historique_datacenter = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'datacenter'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
            models.Index(fields=['latitude']),
            models.Index(fields=['longitude']),
        ]
        unique_together = ['name', 'owner']

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    def get_firewall_count(self):
        from firewall_service.models import Firewall
        return Firewall.objects.filter(data_center_id=self.id).count()

    def get_firewall_type_count(self):
        from firewall_service.models import FirewallType
        return FirewallType.objects.filter(data_center_id=self.id).count()

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_datacenter:
            self.historique_datacenter = {'entries': []}
        
        self.historique_datacenter['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='datacenter',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        ) 