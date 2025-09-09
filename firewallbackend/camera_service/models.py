from django.db import models
from django.conf import settings
from .utils import parse_coordinates, format_location
from django.utils import timezone
import uuid
from auth_service.models import User
from history_service.models import ServiceHistory

class Camera(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=str)  # Changed to CharField with UUID length
    name = models.CharField(max_length=100)
    ip_address = models.CharField(max_length=45)  # IPv6 compatible
    location = models.CharField(max_length=255, blank=True)
    latitude = models.CharField(max_length=20, null=True, blank=True)
    longitude = models.CharField(max_length=20, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cameras', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=False)
    last_ping = models.DateTimeField(null=True, blank=True)
    historique_camera = models.JSONField(default=dict, blank=True)
    last_ping_all = models.DateTimeField(null=True, blank=True)  # Ajout du champ pour suivre le dernier ping_all

    class Meta:
        db_table = 'camera'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_online']),
            models.Index(fields=['last_ping']),
            models.Index(fields=['last_ping_all']),  # Ajout de l'index
        ]

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    def save(self, *args, **kwargs):
        # Generate UUID if not set
        if not self.id:
            self.id = str(uuid.uuid4())
            
        # Parse les coordonnées lors de la sauvegarde
        if self.location:
            coords = parse_coordinates(self.location)
            if coords:
                self.latitude, self.longitude = coords
        
        super().save(*args, **kwargs)

    def get_location_decimal(self) -> str:
        """Retourne les coordonnées en format décimal."""
        if self.latitude is not None and self.longitude is not None:
            return f"{float(self.latitude):.6f}, {float(self.longitude):.6f}"
        return self.location

    def get_location_dms(self) -> str:
        """Retourne les coordonnées en format DMS."""
        if self.latitude is not None and self.longitude is not None:
            from .utils import decimal_to_dms
            lat_dms = decimal_to_dms(float(self.latitude), True)
            lng_dms = decimal_to_dms(float(self.longitude), False)
            return f"{lat_dms} {lng_dms}"
        return self.location

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_camera:
            self.historique_camera = {'entries': []}
        
        self.historique_camera['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='camera',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

    def __str__(self):
        return f"{self.name} ({self.ip_address}) - {self.owner.username if self.owner else 'No owner'}"

class PingResult(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=str)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='ping_results')
    status = models.CharField(max_length=20)  # 'online', 'offline', 'error'
    response_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    task_id = models.CharField(max_length=50, null=True, blank=True)  # Pour lier les résultats à une tâche de ping_all

    class Meta:
        db_table = 'ping_result'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['camera']),
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['task_id']),
        ]

    def __str__(self):
        return f"Ping result for {self.camera.name} at {self.timestamp}" 