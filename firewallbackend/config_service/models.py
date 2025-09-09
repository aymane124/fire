from django.db import models
from django.utils import timezone
import uuid
from auth_service.models import User
from firewall_service.models import Firewall

class FirewallConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firewall = models.ForeignKey(Firewall, on_delete=models.CASCADE, related_name='configurations')
    config_data = models.JSONField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='firewall_configs')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'firewall_config'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['firewall']),
            models.Index(fields=['owner']),
            models.Index(fields=['created_at']),
            models.Index(fields=['version']),
        ]

    def __str__(self):
        return f"Config for {self.firewall.name} (v{self.version})"

    def save(self, *args, **kwargs):
        if not self.id:  # New config
            last_version = FirewallConfig.objects.filter(
                firewall=self.firewall
            ).order_by('-version').first()
            if last_version:
                self.version = last_version.version + 1
        super().save(*args, **kwargs)
