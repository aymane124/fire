#!/usr/bin/env python
import re
import logging
import asyncio
from typing import List, Dict, Any
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import FirewallInterfaceAlert, InterfaceStatusLog
from websocket_service.ssh_session_manager import execute_command_via_ssh
from auth_service.models import User

logger = logging.getLogger(__name__)


class InterfaceAnalyzer:
    """Analyseur pour détecter les interfaces down dans la sortie des commandes"""
    
    def __init__(self):
        self.patterns = {
            'cisco': {
                'interface_pattern': r'(\w+/\d+/\d+|\w+/\d+|\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)',
                'status_keywords': ['up', 'down', 'administratively down']
            },
            'fortinet': {
                'interface_pattern': r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)',
                'status_keywords': ['up', 'down', 'disabled']
            },
            'generic': {
                'interface_pattern': r'(\w+)\s+(\w+)\s+(\w+)',
                'status_keywords': ['up', 'down', 'disabled', 'shutdown']
            }
        }
    
    def analyze_interface_output(self, output: str, firewall_type: str = 'generic') -> Dict[str, Any]:
        """Analyser la sortie de la commande d'interface"""
        try:
            pattern = self.patterns.get(firewall_type, self.patterns['generic'])
            lines = output.strip().split('\n')
            
            interfaces = []
            down_interfaces = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                match = re.search(pattern['interface_pattern'], line, re.IGNORECASE)
                if match:
                    interface_info = self._parse_interface_line(match, line, pattern['status_keywords'])
                    if interface_info:
                        interfaces.append(interface_info)
                        if interface_info['status'].lower() in ['down', 'disabled', 'shutdown', 'administratively down']:
                            down_interfaces.append(interface_info)
            
            return {
                'total_interfaces': len(interfaces),
                'up_interfaces': len(interfaces) - len(down_interfaces),
                'down_interfaces': len(down_interfaces),
                'down_interfaces_details': down_interfaces,
                'all_interfaces': interfaces
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des interfaces: {str(e)}")
            return {
                'total_interfaces': 0,
                'up_interfaces': 0,
                'down_interfaces': 0,
                'down_interfaces_details': [],
                'all_interfaces': [],
                'error': str(e)
            }
    
    def _parse_interface_line(self, match, line: str, status_keywords: List[str]) -> Dict[str, Any]:
        """Parser une ligne d'interface"""
        try:
            groups = match.groups()
            
            # Identifier l'interface et le statut
            interface_name = groups[0] if groups else None
            status = None
            
            # Chercher le statut dans les mots-clés
            for group in groups:
                if group and group.lower() in status_keywords:
                    status = group
                    break
            
            # Si pas de statut trouvé, essayer de le détecter dans la ligne
            if not status:
                for keyword in status_keywords:
                    if keyword.lower() in line.lower():
                        status = keyword
                        break
            
            if interface_name and status:
                return {
                    'name': interface_name,
                    'status': status,
                    'raw_line': line
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur parsing ligne interface: {str(e)}")
            return None


class InterfaceMonitorService:
    """Service de surveillance des interfaces firewall"""
    
    def __init__(self):
        self.analyzer = InterfaceAnalyzer()
    
    async def check_all_alerts(self):
        """Vérifier toutes les alertes actives"""
        try:
            from asgiref.sync import sync_to_async
            active_alerts = await sync_to_async(list)(FirewallInterfaceAlert.objects.filter(is_active=True))
            
            for alert in active_alerts:
                await self.check_alert(alert)
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des alertes: {str(e)}")
    
    async def check_alert(self, alert: FirewallInterfaceAlert):
        """Vérifier une alerte spécifique"""
        try:
            # Vérifier si c'est le moment de faire la vérification
            if not await self._should_check_now(alert):
                return
            
            logger.info(f"Vérification de l'alerte: {alert.name}")
            
            # Vérifier chaque firewall
            all_down_interfaces = []
            
            firewalls = await sync_to_async(list)(alert.firewalls.all())
            for firewall in firewalls:
                try:
                    result = await self._check_firewall_interfaces(firewall, alert)
                    if result and result['down_interfaces'] > 0:
                        all_down_interfaces.append({
                            'firewall': firewall,
                            'result': result
                        })
                except Exception as e:
                    logger.error(f"Erreur vérification firewall {firewall.name}: {str(e)}")
            
            # Si des interfaces sont down, envoyer l'alerte
            if all_down_interfaces:
                await self._send_interface_alert(alert, all_down_interfaces)
            
            # Mettre à jour la dernière vérification
            alert.last_check = timezone.now()
            await sync_to_async(alert.save)()
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'alerte {alert.name}: {str(e)}")
    
    async def _should_check_now(self, alert: FirewallInterfaceAlert) -> bool:
        """Vérifier si c'est le moment de faire la vérification"""
        if not alert.last_check:
            return True
        
        interval = timezone.timedelta(minutes=alert.check_interval_minutes)
        return timezone.now() - alert.last_check >= interval
    
    async def _check_firewall_interfaces(self, firewall, alert: FirewallInterfaceAlert) -> Dict[str, Any]:
        """Vérifier les interfaces d'un firewall spécifique"""
        try:
            # Exécuter la commande de vérification
            command = alert.interface_check_command
            command_id = f"interface_check_{firewall.id}_{int(timezone.now().timestamp())}"
            
            # Utiliser un utilisateur admin pour l'exécution
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                logger.error("Aucun utilisateur admin trouvé")
                return None
            
            output = await execute_command_via_ssh(firewall, command, command_id, admin_user)
            
            # Analyser la sortie
            firewall_type = getattr(firewall.firewall_type, 'name', 'generic').lower()
            analysis_result = self.analyzer.analyze_interface_output(output, firewall_type)
            
            # Créer le log
            status_log = InterfaceStatusLog.objects.create(
                alert=alert,
                firewall=firewall,
                command_executed=command,
                raw_output=output,
                total_interfaces=analysis_result['total_interfaces'],
                up_interfaces=analysis_result['up_interfaces'],
                down_interfaces=analysis_result['down_interfaces'],
                down_interfaces_details=analysis_result['down_interfaces_details'],
                alert_triggered=analysis_result['down_interfaces'] > 0
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Erreur vérification interfaces firewall {firewall.name}: {str(e)}")
            return None
    
    async def _send_interface_alert(self, alert: FirewallInterfaceAlert, down_interfaces_data: List[Dict]):
        """Envoyer l'alerte par email"""
        try:
            # Préparer le contenu de l'email
            subject = f"🚨 ALERTE: Interfaces Firewall Down - {alert.name}"
            
            # Construire le contenu HTML
            html_content = self._build_alert_email_content(alert, down_interfaces_data)
            
            # Envoyer l'email aux destinataires
            recipients = alert.get_recipients()
            recipient_emails = [user.email for user in recipients if user.email]
            
            if recipient_emails:
                send_mail(
                    subject=subject,
                    message='',  # Version texte vide
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_emails,
                    html_message=html_content,
                    fail_silently=False
                )
                
                # Mettre à jour le statut
                alert.last_alert_sent = timezone.now()
                alert.save()
                
                # Marquer les logs comme alertes envoyées
                for data in down_interfaces_data:
                    firewall = data['firewall']
                    await sync_to_async(InterfaceStatusLog.objects.filter(
                        alert=alert,
                        firewall=firewall,
                        alert_triggered=True,
                        alert_sent=False
                    ).update)(
                        alert_sent=True,
                        alert_sent_at=timezone.now()
                    )
                
                logger.info(f"Alerte envoyée pour {alert.name} à {len(recipient_emails)} destinataires")
            else:
                logger.warning(f"Aucun destinataire email trouvé pour l'alerte {alert.name}")
                
        except Exception as e:
            logger.error(f"Erreur envoi alerte email: {str(e)}")
    
    def _build_alert_email_content(self, alert: FirewallInterfaceAlert, down_interfaces_data: List[Dict]) -> str:
        """Construire le contenu HTML de l'email d'alerte"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #ff4444; color: white; padding: 20px; border-radius: 5px; }}
                .firewall-section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .interface-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .interface-table th, .interface-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .interface-table th {{ background-color: #f5f5f5; }}
                .status-down {{ color: #ff4444; font-weight: bold; }}
                .summary {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 ALERTE INTERFACES FIREWALL</h1>
                <p><strong>Alerte:</strong> {alert.name}</p>
                <p><strong>Heure de détection:</strong> {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Résumé</h2>
                <p><strong>Nombre de firewalls affectés:</strong> {len(down_interfaces_data)}</p>
                <p><strong>Total d'interfaces down:</strong> {sum(data['result']['down_interfaces'] for data in down_interfaces_data)}</p>
            </div>
        """
        
        for data in down_interfaces_data:
            firewall = data['firewall']
            result = data['result']
            
            html += f"""
            <div class="firewall-section">
                <h3>🖥️ Firewall: {firewall.name} ({firewall.ip_address})</h3>
                <p><strong>Type:</strong> {firewall.firewall_type.name}</p>
                <p><strong>Interfaces totales:</strong> {result['total_interfaces']}</p>
                <p><strong>Interfaces up:</strong> {result['up_interfaces']}</p>
                <p class="status-down"><strong>Interfaces down:</strong> {result['down_interfaces']}</p>
                
                <h4>📋 Détails des interfaces down:</h4>
                <table class="interface-table">
                    <thead>
                        <tr>
                            <th>Interface</th>
                            <th>Statut</th>
                            <th>Informations</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for interface in result['down_interfaces_details']:
                html += f"""
                        <tr>
                            <td><strong>{interface['name']}</strong></td>
                            <td class="status-down">{interface['status']}</td>
                            <td>{interface.get('raw_line', 'N/A')}</td>
                        </tr>
                """
            
            html += """
                    </tbody>
                </table>
            </div>
            """
        
        html += f"""
            <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <p><strong>⚠️ Actions recommandées:</strong></p>
                <ul>
                    <li>Vérifier la connectivité physique des interfaces</li>
                    <li>Contrôler les configurations des interfaces</li>
                    <li>Vérifier les logs système pour identifier la cause</li>
                    <li>Contacter l'équipe réseau si nécessaire</li>
                </ul>
            </div>
            
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>Cette alerte a été générée automatiquement par le système de surveillance des interfaces firewall.</p>
                <p>Pour plus d'informations, connectez-vous à l'interface d'administration.</p>
            </div>
        </body>
        </html>
        """
        
        return html


# Instance globale du service
interface_monitor_service = InterfaceMonitorService()


async def run_interface_monitoring():
    """Fonction principale pour exécuter la surveillance des interfaces"""
    try:
        await interface_monitor_service.check_all_alerts()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la surveillance: {str(e)}")


# Fonction pour exécuter manuellement la vérification d'une alerte
async def check_alert_manually(alert_id: str):
    """Vérifier manuellement une alerte spécifique"""
    try:
        alert = FirewallInterfaceAlert.objects.get(id=alert_id)
        await interface_monitor_service.check_alert(alert)
        return True
    except FirewallInterfaceAlert.DoesNotExist:
        logger.error(f"Alerte {alert_id} non trouvée")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification manuelle: {str(e)}")
        return False
