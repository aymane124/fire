from django.db import models
from django.utils import timezone
import uuid

class DashboardStats(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    total_firewalls = models.IntegerField(default=0)
    active_firewalls = models.IntegerField(default=0)
    total_datacenters = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    recent_commands = models.IntegerField(default=0)
    pending_tasks = models.IntegerField(default=0)
    system_health = models.CharField(max_length=20, default='warning')
    last_updated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'dashboard_stats'
        verbose_name = 'Dashboard Statistics'
        verbose_name_plural = 'Dashboard Statistics'
    
    def __str__(self):
        return f"Dashboard Stats - {self.last_updated.strftime('%Y-%m-%d %H:%M')}"
