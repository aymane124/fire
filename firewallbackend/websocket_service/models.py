from django.db import models
from django.contrib.auth import get_user_model
from firewall_service.models import Firewall
import uuid

User = get_user_model()


class TerminalSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terminal_sessions')
    firewall = models.ForeignKey(Firewall, on_delete=models.CASCADE, related_name='terminal_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'terminal_session'
        verbose_name = 'Terminal Session'
        verbose_name_plural = 'Terminal Sessions'

    def __str__(self):
        return f"Session {self.session_id} - {self.firewall.name}"


class TerminalCommand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TerminalSession, on_delete=models.CASCADE, related_name='commands')
    command = models.TextField()
    command_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=[
        ('executing', 'Executing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='executing')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_command'
        verbose_name = 'Terminal Command'
        verbose_name_plural = 'Terminal Commands'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.command[:50]}... - {self.status}"
