import logging
from asgiref.sync import sync_to_async
import asyncio
from typing import List, Dict, Any
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email_service.models import EmailLog
from .models import InterfaceAlert

logger = logging.getLogger(__name__)


class AlertEmailService:
    """Service d'envoi d'alertes par email pour les interfaces"""
    
    def __init__(self, alert: InterfaceAlert, current_firewall: Any = None):
        self.alert = alert
        # Utiliser le firewall courant si fourni (exécution par type), sinon l'attacher de l'alerte
        self.firewall = current_firewall or alert.firewall
        self.logger = logging.getLogger(__name__)
    
    async def send_interface_alert(self, interfaces: List[Dict[str, Any]], alerts_triggered: List[Dict[str, Any]], recipients: List[Any] = None) -> int:
        """
        Envoie une alerte par email pour les interfaces
        
        Args:
            interfaces: Liste des interfaces avec leur statut
            alerts_triggered: Liste des alertes déclenchées
            
        Returns:
            Nombre d'emails envoyés avec succès
        """
        try:
            # Récupérer les destinataires (ORM via executor) si non fournis
            if recipients is None:
                recipients = await sync_to_async(self.alert.get_recipients, thread_sensitive=False)()
            
            if not recipients:
                self.logger.warning(f"Aucun destinataire trouvé pour l'alerte: {self.alert.name}")
                return 0
            
            # Ne notifier que les interfaces réellement en panne
            problem_interfaces = [a.get('interface') for a in alerts_triggered if a.get('interface')]

            # Préparer le contenu de l'email uniquement avec les interfaces down
            subject = self._prepare_alert_subject(alerts_triggered)
            html_content = self._prepare_alert_html(problem_interfaces, alerts_triggered)
            text_content = self._prepare_alert_text(problem_interfaces, alerts_triggered)
            
            # Envoyer l'email à chaque destinataire
            emails_sent = 0
            for recipient in recipients:
                try:
                    success = await self._send_single_email(
                        recipient.email,
                        subject,
                        html_content,
                        text_content
                    )
                    
                    if success:
                        emails_sent += 1
                        self.logger.info(f"Email d'alerte envoyé à: {recipient.email}")
                    else:
                        self.logger.error(f"Échec de l'envoi d'email à: {recipient.email}")
                        
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi d'email à {recipient.email}: {str(e)}")
            
            self.logger.info(f"Envoi d'alertes terminé: {emails_sent}/{len(recipients)} emails envoyés")
            return emails_sent
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi des alertes: {str(e)}")
            return 0
    
    async def send_error_alert(self, error_message: str, recipients: List[Any] = None) -> int:
        """
        Envoie une alerte d'erreur par email
        
        Args:
            error_message: Message d'erreur à envoyer
            
        Returns:
            Nombre d'emails envoyés avec succès
        """
        try:
            # Récupérer les destinataires (priorité aux admins pour les erreurs)
            if recipients is None:
                recipients = await sync_to_async(self.alert.get_recipients, thread_sensitive=False)()
            
            if not recipients:
                self.logger.warning(f"Aucun destinataire trouvé pour l'alerte d'erreur: {self.alert.name}")
                return 0
            
            # Préparer le contenu de l'email d'erreur
            subject = f"ERREUR: {self.alert.name} - Problème de surveillance"
            html_content = self._prepare_error_html(error_message)
            text_content = self._prepare_error_text(error_message)
            
            # Envoyer l'email d'erreur
            emails_sent = 0
            for recipient in recipients:
                try:
                    success = await self._send_single_email(
                        recipient.email,
                        subject,
                        html_content,
                        text_content
                    )
                    
                    if success:
                        emails_sent += 1
                        
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi de l'email d'erreur à {recipient.email}: {str(e)}")
            
            return emails_sent
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi de l'alerte d'erreur: {str(e)}")
            return 0
    
    def _prepare_alert_subject(self, alerts_triggered: List[Dict[str, Any]]) -> str:
        """Prépare le sujet de l'email d'alerte"""
        if not alerts_triggered:
            return f"INFO: {self.alert.name} - Statut des interfaces"
        
        # Compter les types d'alertes
        down_count = len([a for a in alerts_triggered if a['interface']['status'] == 'down'])
        error_count = len([a for a in alerts_triggered if a['interface']['status'] == 'error'])
        
        if down_count > 0:
            return f"ALERTE CRITIQUE: {self.alert.name} - {down_count} interface(s) down"
        elif error_count > 0:
            return f"ALERTE: {self.alert.name} - {error_count} interface(s) en erreur"
        else:
            return f"ALERTE: {self.alert.name} - Conditions d'alerte déclenchées"
    
    def _prepare_alert_html(self, interfaces: List[Dict[str, Any]], alerts_triggered: List[Dict[str, Any]]) -> str:
        """Prépare le contenu HTML de l'email d'alerte"""
        try:
            # Utiliser un template HTML si disponible, sinon créer un HTML basique
            context = {
                'alert': self.alert,
                'firewall': self.firewall,
                'interfaces': interfaces,  # liste filtrée: seulement DOWN
                'alerts_triggered': alerts_triggered,
                'timestamp': timezone.now(),
                'summary': self._calculate_summary(interfaces)  # résumé des DOWN uniquement
            }
            
            # Essayer de rendre un template, sinon utiliser le HTML par défaut
            try:
                html_content = render_to_string('emails/interface_alert.html', context)
            except:
                html_content = self._generate_default_html(context)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation du HTML: {str(e)}")
            return self._generate_fallback_html()
    
    def _prepare_alert_text(self, interfaces: List[Dict[str, Any]], alerts_triggered: List[Dict[str, Any]]) -> str:
        """Prépare le contenu texte de l'email d'alerte"""
        try:
            fw_name = getattr(self.firewall, 'name', 'N/A')
            text_content = f"""
ALERTE: {self.alert.name}
Firewall: {fw_name}
Heure: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Résumé (interfaces down uniquement):
- Interfaces down: {len(interfaces)}

Interfaces down:
"""
            
            for interface in interfaces:
                iface_ip = interface.get('ip_address', 'N/A')
                fw_name = getattr(self.firewall, 'name', 'N/A')
                text_content += f"- {interface.get('name','N/A')} (IP: {iface_ip}, FW: {fw_name}): down\n"
            
            # Détails succincts seulement pour les interfaces down
            text_content += "\nDétails des interfaces down:\n"
            for interface in interfaces:
                line = f"- {interface.get('name','N/A')}: down"
                if interface.get('ip_address'):
                    line += f" - IP: {interface['ip_address']}"
                text_content += line + "\n"
            
            return text_content.strip()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation du texte: {str(e)}")
            return f"Erreur lors de la préparation de l'alerte: {str(e)}"
    
    def _prepare_error_html(self, error_message: str) -> str:
        """Prépare le contenu HTML de l'email d'erreur"""
        try:
            context = {
                'alert': self.alert,
                'firewall': self.firewall,
                'error_message': error_message,
                'timestamp': timezone.now()
            }
            
            try:
                html_content = render_to_string('emails/interface_error.html', context)
            except:
                html_content = self._generate_error_html(context)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation du HTML d'erreur: {str(e)}")
            return self._generate_fallback_error_html(error_message)
    
    def _prepare_error_text(self, error_message: str) -> str:
        """Prépare le contenu texte de l'email d'erreur"""
        fw_name = getattr(self.firewall, 'name', 'N/A')
        return f"""
ERREUR: {self.alert.name}
Firewall: {fw_name}
Heure: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Une erreur s'est produite lors de la surveillance des interfaces:

{error_message}

Veuillez vérifier la configuration et l'état du firewall.
"""
    
    def _generate_default_html(self, context: Dict[str, Any]) -> str:
        """Génère un HTML par défaut si aucun template n'est disponible"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Alerte Interface</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .critical {{ background-color: #f8d7da; border-color: #f5c6cb; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .table th {{ background-color: #f2f2f2; }}
        .status-up {{ color: #28a745; }}
        .status-down {{ color: #dc3545; }}
        .status-error {{ color: #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🚨 ALERTE: {context['alert'].name}</h2>
        <p><strong>Firewall:</strong> {context['firewall'].name}</p>
        <p><strong>Heure:</strong> {context['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="alert">
        <h3>📊 Résumé</h3>
        <p>Interfaces vérifiées: {context['summary']['total_interfaces']}</p>
        <p>Interfaces UP: <span class="status-up">{context['summary']['up_interfaces']}</span></p>
        <p>Interfaces DOWN: <span class="status-down">{context['summary']['down_interfaces']}</span></p>
        <p>Interfaces en erreur: <span class="status-error">{context['summary']['error_interfaces']}</span></p>
        <p>Santé globale: {context['summary']['health_percentage']}%</p>
    </div>
    
    <h3>🔍 Détails des interfaces</h3>
    <table class="table">
        <thead>
            <tr>
                <th>Interface</th>
                <th>Statut</th>
                <th>IP</th>
                <th>Bande passante In</th>
                <th>Bande passante Out</th>
                <th>Erreurs</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for interface in context['interfaces']:
            status_class = f"status-{interface['status']}"
            html += f"""
            <tr>
                <td>{interface['name']}</td>
                <td class="{status_class}">{interface['status'].upper()}</td>
                <td>{interface.get('ip_address', 'N/A')}</td>
                <td>{interface.get('bandwidth_in', 'N/A')} Mbps</td>
                <td>{interface.get('bandwidth_out', 'N/A')} Mbps</td>
                <td>{interface.get('error_count', 0)}</td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
    
    <div class="alert">
        <h3>⚠️ Alertes déclenchées</h3>
"""
        
        if context['alerts_triggered']:
            for alert in context['alerts_triggered']:
                iface = alert.get('interface', {})
                iface_name = iface.get('name', 'N/A')
                iface_ip = iface.get('ip_address', 'N/A')
                fw_name = context['firewall'].name if context.get('firewall') else 'N/A'
                html += f"<p>• Interface: <strong>{iface_name}</strong> — IP: <strong>{iface_ip}</strong> — Firewall: <strong>{fw_name}</strong> — {alert['reason']}</p>"
        else:
            html += "<p>Aucune alerte déclenchée</p>"
        
        html += """
    </div>
    
    <p><em>Cet email a été généré automatiquement par le système de surveillance des interfaces.</em></p>
</body>
</html>
"""
        
        return html
    
    def _generate_error_html(self, context: Dict[str, Any]) -> str:
        """Génère un HTML pour les erreurs"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Erreur de Surveillance</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; color: #721c24; }}
    </style>
</head>
<body>
    <div class="error">
        <h2>❌ ERREUR: {context['alert'].name}</h2>
        <p><strong>Firewall:</strong> {context['firewall'].name}</p>
        <p><strong>Heure:</strong> {context['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Erreur:</strong></p>
        <pre>{context['error_message']}</pre>
    </div>
</body>
</html>
"""
    
    def _generate_fallback_html(self) -> str:
        """HTML de fallback en cas d'erreur"""
        return """
<!DOCTYPE html>
<html>
<body>
    <h2>Alerte Interface</h2>
    <p>Une alerte a été déclenchée mais le contenu n'a pas pu être généré.</p>
</body>
</html>
"""
    
    def _generate_fallback_error_html(self, error_message: str) -> str:
        """HTML de fallback pour les erreurs"""
        return f"""
<!DOCTYPE html>
<html>
<body>
    <h2>Erreur de Surveillance</h2>
    <p>Une erreur s'est produite: {error_message}</p>
</body>
</html>
"""
    
    def _calculate_summary(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule un résumé des interfaces"""
        try:
            total = len(interfaces)
            up = len([i for i in interfaces if i['status'] == 'up'])
            down = len([i for i in interfaces if i['status'] == 'down'])
            error = len([i for i in interfaces if i['status'] == 'error'])
            
            return {
                'total_interfaces': total,
                'up_interfaces': up,
                'down_interfaces': down,
                'error_interfaces': error,
                'health_percentage': round((up / total * 100) if total > 0 else 0, 2)
            }
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul du résumé: {str(e)}")
            return {
                'total_interfaces': 0,
                'up_interfaces': 0,
                'down_interfaces': 0,
                'error_interfaces': 0,
                'health_percentage': 0
            }
    
    async def _send_single_email(self, recipient_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Envoie un email à un destinataire"""
        try:
            # Envoyer l'email (thread-safe depuis contexte async)
            await sync_to_async(send_mail, thread_sensitive=False)(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_content,
                fail_silently=False
            )

            # Enregistrer dans les logs (ORM via thread executor)
            await sync_to_async(EmailLog.objects.create, thread_sensitive=False)(
                recipient=recipient_email,
                subject=subject,
                content=text_content,
                status='sent'
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi d'email à {recipient_email}: {str(e)}")
            
            # Enregistrer l'erreur dans les logs
            try:
                await sync_to_async(EmailLog.objects.create, thread_sensitive=False)(
                    recipient=recipient_email,
                    subject=subject,
                    content=text_content,
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass
            
            return False
