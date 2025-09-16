from django.db import models
from firewall_service.models import Firewall
from django.utils import timezone
from history_service.models import ServiceHistory

class DailyCheck(models.Model):
    firewall = models.ForeignKey(Firewall, on_delete=models.CASCADE, related_name='daily_checks')
    check_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, choices=[
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
        ('CONNECTION_FAILED', 'Connection Failed'),
        ('PARTIAL_SUCCESS', 'Partial Success'),
        ('ERROR', 'Error'),
        ('TIMEOUT', 'Timeout')
    ], default='PENDING')
    notes = models.TextField(blank=True, null=True)
    excel_report = models.TextField(null=True, blank=True)
    screenshot_base64 = models.TextField(blank=True, null=True, help_text='Base64 encoded screenshot of the firewall dashboard')
    screenshot_captured = models.BooleanField(default=False, help_text='Whether screenshot was successfully captured')
    historique_dailycheck = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-check_date']

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
            'check_info': {
                'check_date': self.check_date.isoformat(),
                'status': self.status,
                'has_notes': bool(self.notes),
                'has_excel_report': bool(self.excel_report)
            }
        }
        
        if not self.historique_dailycheck:
            self.historique_dailycheck = {'entries': []}
        
        self.historique_dailycheck['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='dailycheck',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

class CheckCommand(models.Model):
    daily_check = models.ForeignKey(DailyCheck, on_delete=models.CASCADE, related_name='commands')
    command = models.TextField()
    expected_output = models.TextField(blank=True, null=True)
    actual_output = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=[
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending')
    ], default='PENDING')
    execution_time = models.DateTimeField(auto_now_add=True)
    historique_dailycheck = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['execution_time']

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address,
            'daily_check_info': {
                'id': str(self.daily_check.id),
                'check_date': self.daily_check.check_date.isoformat(),
                'status': self.daily_check.status
            },
            'command_info': {
                'command': self.command,
                'status': self.status,
                'has_expected_output': bool(self.expected_output),
                'has_actual_output': bool(self.actual_output),
                'execution_time': self.execution_time.isoformat()
            }
        }
        
        if not self.historique_dailycheck:
            self.historique_dailycheck = {'entries': []}
        
        self.historique_dailycheck['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='dailycheck_command',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        ) 