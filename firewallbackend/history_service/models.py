from django.db import models
from django.utils import timezone

class ServiceHistory(models.Model):
    service_name = models.CharField(max_length=100)
    action = models.CharField(max_length=100)  # start, stop, restart, etc.
    status = models.CharField(max_length=50)   # success, failed, etc.
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Service History'
        verbose_name_plural = 'Service Histories'

    def __str__(self):
        return f"{self.service_name} - {self.action} - {self.timestamp}" 