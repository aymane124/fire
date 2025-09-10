import asyncio
from asgiref.sync import sync_to_async
import logging
import re
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.conf import settings
from .simple_ssh import SimpleSSHSession
from .models import InterfaceAlert, InterfaceStatus, AlertExecution
from .parsers import FortiGateInterfaceParser
from .alert_service import AlertEmailService

logger = logging.getLogger(__name__)


class InterfaceMonitorService:
    """Service principal de surveillance des interfaces des firewalls"""
    
    def __init__(self, alert: InterfaceAlert):
        self.alert = alert
        self.firewall = alert.firewall
        self.ssh_manager = None
        self.execution = None
        self.parser = None
    
    async def check_interfaces(self) -> Dict[str, Any]:
        """Vérifie l'état des interfaces pour la cible courante (self.firewall)."""
        try:
            # Créer une entrée d'exécution (ORM via sync_to_async)
            self.execution = await sync_to_async(AlertExecution.objects.create, thread_sensitive=False)(
                alert=self.alert,
                status='running'
            )
            
            logger.info(f"Début de la vérification des interfaces pour l'alerte: {self.alert.name}")
            
            # Se connecter au firewall
            await self._connect_to_firewall()
            
            # Exécuter les commandes définies par l'utilisateur (conditions.commands),
            # sinon fallback à pré-commandes + commande principale
            output = await self._execute_user_defined_or_default_commands()
            
            # Parser la sortie selon le type de firewall
            interfaces = self._parse_interface_output(output)

            # Mode simple: ignorer les mappings, filtrer pour ne garder que les interfaces down pour l'alerte
            # (on conservera tout en base, mais on déclenchera alerte uniquement pour down)
            
            # Vérifier les conditions d'alerte
            alerts_triggered = self._check_alert_conditions(interfaces)
            
            # Envoyer les alertes si nécessaire
            emails_sent = 0
            if alerts_triggered:
                # Respect silence window and cooldown
                if await self._is_silenced():
                    logger.info("Alerte en silencieux (silence_until), envoi d'email ignoré")
                elif not await self._is_past_cooldown():
                    logger.info("Cooldown actif, envoi d'email ignoré")
                else:
                    # N'envoyer que si l'état DOWN a changé depuis la dernière exécution
                    should_send = await self._should_send_emails(alerts_triggered)
                    if should_send:
                        emails_sent = await self._send_alerts(interfaces, alerts_triggered)
                        await self._send_webhook_if_configured(interfaces, alerts_triggered)
                    else:
                        logger.info("Aucun changement d'état DOWN détecté, envoi d'email ignoré")
            else:
                logger.debug(
                    "Aucune alerte déclenchée pour %s. Résumé: up=%d, down=%d, error=%d",
                    self.alert.name,
                    len([i for i in interfaces if i.get('status') == 'up']),
                    len([i for i in interfaces if i.get('status') == 'down']),
                    len([i for i in interfaces if i.get('status') == 'error'])
                )
            
            # Sauvegarder l'état des interfaces (DOWN/ERROR uniquement pour minimiser la charge)
            await self._save_interface_status(interfaces)
            
            # Mettre à jour l'alerte
            await self._update_alert_status(interfaces)
            
            # Marquer l'exécution comme terminée
            # Compter pour le résumé
            total_interfaces = len(interfaces)
            num_up = len([i for i in interfaces if i.get('status') == 'up'])
            num_down = len([i for i in interfaces if i.get('status') == 'down'])
            num_error = len([i for i in interfaces if i.get('status') == 'error'])
            details = {
                'interfaces_checked': len(interfaces),
                'alerts_triggered': len(alerts_triggered),
                'emails_sent': emails_sent,
                'interfaces_status': {i['name']: i['status'] for i in interfaces},
                'down_interfaces': [a['interface']['name'] for a in alerts_triggered if a.get('interface')],
                'counts': {
                    'total': total_interfaces,
                    'up': num_up,
                    'down': num_down,
                    'error': num_error
                }
            }
            await sync_to_async(self.execution.mark_completed, thread_sensitive=False)(details)
            
            logger.info(f"Vérification terminée: {len(interfaces)} interfaces vérifiées, {len(alerts_triggered)} alertes déclenchées")
            
            return {
                'success': True,
                'interfaces_checked': len(interfaces),
                'alerts_triggered': len(alerts_triggered),
                'emails_sent': emails_sent,
                'interfaces': interfaces
            }
            
        except Exception as e:
            error_msg = f"Erreur lors de la vérification des interfaces: {str(e)}"
            logger.error(error_msg)
            
            if self.execution:
                await sync_to_async(self.execution.mark_failed, thread_sensitive=False)(error_msg)
            
            # Envoyer une alerte d'erreur
            await self._send_error_alert(error_msg)
            
            return {
                'success': False,
                'error': str(e)
            }
        
        finally:
            # Fermer la connexion SSH
            await self._disconnect_ssh()

    async def _execute_user_defined_or_default_commands(self) -> str:
        """Exécute la séquence de commandes souhaitée par l'utilisateur.

        conditions.commands: ["config global", "show system interface", ...]
        conditions.parse_from: "last" | "first" | index (int) | "concat"
        
        Retourne la sortie sélectionnée pour le parsing.
        """
        conditions = self.alert.conditions or {}
        commands = conditions.get('commands')
        parse_from = conditions.get('parse_from', 'last')

        if isinstance(commands, list) and commands:
            outputs: List[str] = []
            for idx, cmd in enumerate(commands):
                if not isinstance(cmd, str) or not cmd.strip():
                    continue
                command_id = f"ucmd_{idx}_{int(timezone.now().timestamp())}"
                out = await self.ssh_manager.execute_command(cmd.strip(), command_id)
                outputs.append(out or "")

            # Sélection de la sortie à parser
            if not outputs:
                raise Exception("Aucune sortie obtenue des commandes utilisateur")

            if parse_from == 'first':
                return outputs[0]
            if parse_from == 'concat':
                return "\n".join(outputs)
            if isinstance(parse_from, int) and 0 <= parse_from < len(outputs):
                return outputs[parse_from]
            # default 'last'
            return outputs[-1]

        # Fallback ancien comportement
        await self._run_pre_commands_if_any()
        return await self._execute_interface_command()
    
    async def _connect_to_firewall(self):
        """Établit la connexion SSH au firewall"""
        try:
            self.ssh_manager = SimpleSSHSession(self.firewall)
            await self.ssh_manager.connect()
            logger.info(f"Connexion SSH établie au firewall: {self.firewall.name}")
            # Initialiser le parser maintenant que la cible est connue
            try:
                fw_type_name = ''
                if hasattr(self.firewall, 'firewall_type'):
                    ft = getattr(self.firewall, 'firewall_type')
                    fw_type_name = getattr(ft, 'name', ft)
                if isinstance(fw_type_name, str) and fw_type_name.lower() in ['forti', 'fortigate', 'fortinet', 'fortigate-fw']:
                    self.parser = FortiGateInterfaceParser()
                else:
                    self.parser = FortiGateInterfaceParser()
            except Exception:
                self.parser = FortiGateInterfaceParser()
            
        except Exception as e:
            logger.error(f"Erreur de connexion SSH: {str(e)}")
            raise Exception(f"Impossible de se connecter au firewall {self.firewall.name}: {str(e)}")
    
    async def _execute_interface_command(self) -> str:
        """Exécute la commande de vérification des interfaces"""
        try:
            command = self.alert.command_template or "show system interface"
            
            # Créer un ID de commande temporaire
            command_id = f"interface_check_{int(timezone.now().timestamp())}"
            
            # Exécuter la commande
            output = await self.ssh_manager.execute_command(command, command_id)
            
            logger.info(f"Commande exécutée: {command}")
            logger.debug(f"Sortie de la commande: {output[:500]}...")
            
            return output
            
        except Exception as e:
            logger.error(f"Erreur d'exécution de la commande: {str(e)}")
            raise Exception(f"Erreur lors de l'exécution de la commande: {str(e)}")

    async def _run_pre_commands_if_any(self):
        """Exécute les pré-commandes définies dans conditions.pre_commands dans la même session SSH."""
        try:
            conditions = self.alert.conditions or {}
            pre_commands = conditions.get('pre_commands', [])
            if not pre_commands:
                return

            for idx, pre_cmd in enumerate(pre_commands):
                if not isinstance(pre_cmd, str) or not pre_cmd.strip():
                    continue
                command_id = f"precmd_{idx}_{int(timezone.now().timestamp())}"
                _ = await self.ssh_manager.execute_command(pre_cmd.strip(), command_id)
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution des pré-commandes: {str(e)}")
            # On continue tout de même pour ne pas bloquer la vérification principale
    
    def _parse_interface_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse la sortie de la commande selon le type de firewall"""
        try:
            if self.parser:
                interfaces = self.parser.parse(output)
            else:
                # Parser générique
                interfaces = self._generic_parse(output)
            
            logger.info(f"Parsing terminé: {len(interfaces)} interfaces détectées")
            return interfaces
            
        except Exception as e:
            logger.error(f"Erreur de parsing: {str(e)}")
            # Retourner une liste vide en cas d'erreur
            return []

    def _apply_mappings_if_any(self, interfaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Applique des règles de mapping définies dans conditions.mappings.

        Format attendu (exemples):
          conditions: {
            "mappings": [
              {"field": "raw_output", "pattern": "status:\\s*down", "set": {"status": "down"}},
              {"field": "name", "pattern": "^port\\d+$", "set": {"status": "up"}}
            ]
          }
        """
        try:
            conditions = self.alert.conditions or {}
            mappings = conditions.get('mappings', [])
            if not mappings:
                return interfaces

            for interface in interfaces:
                for rule in mappings:
                    try:
                        field = (rule.get('field') or 'raw_output')
                        pattern = rule.get('pattern')
                        set_values = rule.get('set') or {}
                        if not pattern or field not in interface:
                            continue
                        value_to_test = str(interface.get(field, ''))
                        if re.search(pattern, value_to_test, flags=re.IGNORECASE):
                            # Appliquer les valeurs
                            for k, v in set_values.items():
                                interface[k] = v
                    except Exception as inner_e:
                        logger.error(f"Erreur règle mapping: {str(inner_e)}")
                        continue
            return interfaces
        except Exception as e:
            logger.error(f"Erreur lors de l'application des mappings: {str(e)}")
            return interfaces
    
    def _generic_parse(self, output: str) -> List[Dict[str, Any]]:
        """Parser générique pour les firewalls non-FortiGate"""
        interfaces = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Logique de parsing générique
                interface = {
                    'name': line.split()[0] if line.split() else 'unknown',
                    'status': 'unknown',
                    'bandwidth_in': 0,
                    'bandwidth_out': 0,
                    'error_count': 0,
                    'ip_address': None,
                    'mac_address': None
                }
                interfaces.append(interface)
        
        return interfaces
    
    def _check_alert_conditions(self, interfaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Vérifie les conditions d'alerte pour chaque interface"""
        alerts_triggered = []
        
        for interface in interfaces:
            should_alert = False
            alert_reason = ""
            
            if self.alert.alert_type == 'interface_down':
                if interface['status'] == 'down':
                    should_alert = True
                    alert_reason = "Interface down"
            
            elif self.alert.alert_type == 'interface_up':
                if interface['status'] == 'up':
                    should_alert = True
                    alert_reason = "Interface up"
            
            elif self.alert.alert_type == 'bandwidth_high':
                if self.alert.threshold_value:
                    if (interface['bandwidth_in'] and interface['bandwidth_in'] > self.alert.threshold_value) or \
                       (interface['bandwidth_out'] and interface['bandwidth_out'] > self.alert.threshold_value):
                        should_alert = True
                        alert_reason = f"Bande passante élevée (> {self.alert.threshold_value} Mbps)"
            
            elif self.alert.alert_type == 'error_count':
                if self.alert.threshold_value and interface['error_count'] > self.alert.threshold_value:
                    should_alert = True
                    alert_reason = f"Nombre d'erreurs élevé (> {self.alert.threshold_value})"
            
            elif self.alert.alert_type == 'custom':
                # Vérifier les conditions personnalisées
                should_alert = self._check_custom_conditions(interface)
                alert_reason = "Condition personnalisée"
            
            if should_alert:
                alerts_triggered.append({
                    'interface': interface,
                    'reason': alert_reason,
                    'alert_type': self.alert.alert_type
                })
        
        return alerts_triggered

    async def _should_send_emails(self, alerts_triggered: List[Dict[str, Any]]) -> bool:
        """Retourne True si la liste des interfaces DOWN a changé depuis la dernière exécution."""
        try:
            current_down = sorted([a['interface']['name'] for a in alerts_triggered if a.get('interface')])
            # Récupérer la dernière exécution terminée
            last_exec = await sync_to_async(
                lambda: AlertExecution.objects.filter(alert=self.alert, status='completed').order_by('-started_at').first(),
                thread_sensitive=False
            )()
            if not last_exec or not last_exec.details:
                return len(current_down) > 0
            prev_details = last_exec.details or {}
            if 'down_interfaces' in prev_details:
                prev_down = sorted(prev_details.get('down_interfaces') or [])
            else:
                # Fallback depuis interfaces_status
                interfaces_status = prev_details.get('interfaces_status') or {}
                prev_down = sorted([name for name, st in interfaces_status.items() if st == 'down'])
            return current_down != prev_down and len(current_down) > 0
        except Exception as e:
            logger.error(f"Erreur comparaison état DOWN: {str(e)}")
            return True

    async def _is_past_cooldown(self) -> bool:
        """Respecte un cooldown configurable via conditions.cooldown_minutes."""
        try:
            conditions = self.alert.conditions or {}
            minutes = int(conditions.get('cooldown_minutes', 0) or 0)
            if minutes <= 0:
                return True
            last_exec = await sync_to_async(
                lambda: AlertExecution.objects.filter(alert=self.alert, status='completed').order_by('-started_at').first(),
                thread_sensitive=False
            )()
            if not last_exec or not last_exec.completed_at:
                return True
            return (timezone.now() - last_exec.completed_at) >= timezone.timedelta(minutes=minutes)
        except Exception:
            return True

    async def _is_silenced(self) -> bool:
        """Silence temporaire via conditions.silence_until (ISO datetime)."""
        try:
            conditions = self.alert.conditions or {}
            silence_until = conditions.get('silence_until')
            if not silence_until:
                return False
            try:
                dt = timezone.datetime.fromisoformat(silence_until)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
            except Exception:
                return False
            return timezone.now() < dt
        except Exception:
            return False

    async def _send_webhook_if_configured(self, interfaces: List[Dict[str, Any]], alerts_triggered: List[Dict[str, Any]]):
        """Envoie un webhook optionnel (conditions.webhook_url) avec les interfaces down."""
        try:
            import json
            import urllib.request
            conditions = self.alert.conditions or {}
            url = conditions.get('webhook_url')
            if not url:
                return
            down = [a.get('interface') for a in alerts_triggered if a.get('interface')]
            payload = {
                'alert_id': str(self.alert.id),
                'alert_name': self.alert.name,
                'firewall': self.firewall.name,
                'down_interfaces': [{
                    'name': i.get('name'), 'ip': i.get('ip_address')
                } for i in down if i],
                'timestamp': timezone.now().isoformat()
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
        except Exception as e:
            logger.error(f"Webhook notify error: {str(e)}")
    
    def _check_custom_conditions(self, interface: Dict[str, Any]) -> bool:
        """Vérifie les conditions personnalisées définies dans l'alerte"""
        if not self.alert.conditions:
            return False
        
        try:
            # Exemple de conditions personnalisées
            conditions = self.alert.conditions
            
            for condition in conditions:
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')
                
                if not all([field, operator, value]):
                    continue
                
                interface_value = interface.get(field)
                
                if operator == 'equals' and interface_value == value:
                    return True
                elif operator == 'not_equals' and interface_value != value:
                    return True
                elif operator == 'greater_than' and interface_value and interface_value > value:
                    return True
                elif operator == 'less_than' and interface_value and interface_value < value:
                    return True
                elif operator == 'contains' and str(value) in str(interface_value):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des conditions personnalisées: {str(e)}")
            return False
    
    async def _send_alerts(self, interfaces: List[Dict[str, Any]], alerts_triggered: List[Dict[str, Any]]) -> int:
        """Envoie les alertes par email"""
        try:
            conditions = self.alert.conditions or {}
            if conditions.get('aggregate_email'):
                # L'envoi sera effectué en mode agrégé au niveau appelant
                return 0
            alert_service = AlertEmailService(self.alert, current_firewall=self.firewall)
            recipients = await sync_to_async(self.alert.get_recipients, thread_sensitive=False)()
            emails_sent = await alert_service.send_interface_alert(interfaces, alerts_triggered, recipients=recipients)
            
            logger.info(f"{emails_sent} emails d'alerte envoyés")
            return emails_sent
            
        except Exception as e:
            logger.error(f"Erreur d'envoi des alertes: {str(e)}")
            return 0
    
    async def _send_error_alert(self, error_message: str):
        """Envoie une alerte d'erreur"""
        try:
            alert_service = AlertEmailService(self.alert, current_firewall=self.firewall)
            await alert_service.send_error_alert(error_message)
            
        except Exception as e:
            logger.error(f"Erreur d'envoi de l'alerte d'erreur: {str(e)}")
    
    async def _save_interface_status(self, interfaces: List[Dict[str, Any]]):
        """Sauvegarde l'état des interfaces en base de données"""
        try:
            def _build_models():
                objs = []
                for data in interfaces:
                    # Option: ne persister que DOWN/ERROR
                    if data.get('status') not in ('down', 'error'):
                        continue
                    raw = (data.get('raw_output') or '')
                    if len(raw) > 1000:
                        raw = raw[:1000]
                    objs.append(InterfaceStatus(
                        alert=self.alert,
                        interface_name=data['name'],
                        status=data['status'],
                        bandwidth_in=data.get('bandwidth_in'),
                        bandwidth_out=data.get('bandwidth_out'),
                        error_count=data.get('error_count', 0),
                        packet_loss=data.get('packet_loss'),
                        ip_address=data.get('ip_address'),
                        mac_address=(data.get('mac_address') or ''),
                        raw_output=raw
                    ))
                return objs

            objs = await sync_to_async(_build_models, thread_sensitive=False)()
            if objs:
                await sync_to_async(InterfaceStatus.objects.bulk_create, thread_sensitive=False)(objs, batch_size=200)
            
            logger.info(f"Statut de {len(interfaces)} interfaces sauvegardé")
            
        except Exception as e:
            logger.error(f"Erreur de sauvegarde du statut des interfaces: {str(e)}")
    
    async def _update_alert_status(self, interfaces: List[Dict[str, Any]]):
        """Met à jour le statut de l'alerte"""
        try:
            # Déterminer le statut global
            if not interfaces:
                global_status = 'unknown'
            elif any(i['status'] == 'down' for i in interfaces):
                global_status = 'down'
            elif all(i['status'] == 'up' for i in interfaces):
                global_status = 'up'
            else:
                global_status = 'mixed'
            
            # Mettre à jour l'alerte (éviter les appels sync dans le contexte async)
            now = timezone.now()
            self.alert.last_check = now
            self.alert.last_status = global_status
            # Imposer un intervalle fixe de 6 minutes
            fixed_seconds = 360
            next_check = now + timezone.timedelta(seconds=fixed_seconds)
            self.alert.next_check = next_check
            await sync_to_async(self.alert.save, thread_sensitive=False)()
            
            logger.info(f"Statut de l'alerte mis à jour: {global_status}")
            logger.info(f"Prochaine vérification programmée à: {next_check} (dans {fixed_seconds} secondes)")
            
        except Exception as e:
            logger.error(f"Erreur de mise à jour du statut de l'alerte: {str(e)}")
    
    async def _disconnect_ssh(self):
        """Ferme la connexion SSH"""
        try:
            if self.ssh_manager:
                # Fermer la connexion SSH
                if hasattr(self.ssh_manager, 'disconnect'):
                    await self.ssh_manager.disconnect()
                else:
                    # Fermeture basique si la méthode n'existe pas
                    if self.ssh_manager.ssh_client:
                        self.ssh_manager.ssh_client.close()
                
                logger.info("Connexion SSH fermée")
                
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture SSH: {str(e)}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Retourne un résumé du statut de surveillance"""
        return {
            'alert_name': self.alert.name,
            'firewall': getattr(self.firewall, 'name', 'unknown'),
            'last_check': self.alert.last_check,
            'next_check': self.alert.next_check,
            'status': self.alert.last_status,
            'is_active': self.alert.is_active
        }
