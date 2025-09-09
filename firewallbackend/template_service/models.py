from django.db import models
from django.conf import settings
from django.utils import timezone
from history_service.models import ServiceHistory

class Variable(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historique_template = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='variables',
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'user']

    def __str__(self):
        return self.name

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_template:
            self.historique_template = {'entries': []}
        
        self.historique_template['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='template_variable',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

class Template(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historique_template = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='templates',
        blank=True,
        null=True
    )
    variables = models.ManyToManyField(
        Variable,
        related_name='templates',
        through='TemplateVariable',
        through_fields=('template', 'variable')
    )

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['name', 'user']

    def __str__(self):
        return self.name

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_template:
            self.historique_template = {'entries': []}
        
        self.historique_template['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='template',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        )

class TemplateVariable(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    variable = models.ForeignKey(Variable, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    historique_template = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ['template', 'variable']
        db_table = 'template_service_template_variables'

    def add_to_history(self, action, status, details=None, user=None, ip_address=None):
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'status': status,
            'details': details,
            'user': str(user) if user else None,
            'ip_address': ip_address
        }
        
        if not self.historique_template:
            self.historique_template = {'entries': []}
        
        self.historique_template['entries'].append(history_entry)
        self.save()

        # Créer une entrée dans le service d'historique
        ServiceHistory.objects.create(
            service_name='template_variable_relation',
            action=action,
            status=status,
            details=details,
            user=str(user) if user else None,
            ip_address=ip_address
        ) 