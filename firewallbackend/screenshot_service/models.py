from django.db import models
from django.utils import timezone
import uuid

class ScreenshotReport(models.Model):
    """
    Modèle pour stocker les rapports de screenshot avec données Excel
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(help_text="Adresse IP du firewall")
    protocol = models.CharField(max_length=10, default='https', help_text="Protocole utilisé (http/https)")
    url = models.URLField(help_text="URL complète du firewall")
    screenshot_base64 = models.TextField(help_text="Screenshot encodé en base64")
    width = models.IntegerField(default=1366, help_text="Largeur du screenshot")
    height = models.IntegerField(default=768, help_text="Hauteur du screenshot")
    excel_file_path = models.CharField(max_length=500, blank=True, null=True, help_text="Chemin vers le fichier Excel généré")
    created_at = models.DateTimeField(default=timezone.now, help_text="Date de création")
    user = models.CharField(max_length=100, blank=True, null=True, help_text="Utilisateur qui a généré le rapport")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Rapport Screenshot"
        verbose_name_plural = "Rapports Screenshots"
    
    def __str__(self):
        return f"Screenshot Report - {self.ip_address} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

