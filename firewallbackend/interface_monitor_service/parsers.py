import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FortiGateInterfaceParser:
    """Parser spécialisé pour les firewalls FortiGate"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Precompile regex for performance
        self._re_interface_header = [
            re.compile(r'^[a-zA-Z0-9_-]+\s+is\s+', re.IGNORECASE),
            re.compile(r'^[a-zA-Z0-9_-]+\s+$'),
            re.compile(r'^Interface\s+[a-zA-Z0-9_-]+', re.IGNORECASE),
        ]
        self._re_ip = re.compile(r'(\d{1,3}(?:\.\d{1,3}){3})')
        self._re_mac = re.compile(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}')
        self._re_bw = re.compile(r'(\d+(?:\.\d+)?)\s*(Mbps|Gbps|Kbps)', re.IGNORECASE)
        self._re_errors = re.compile(r'(\d+)\s+errors?', re.IGNORECASE)
        self._re_pkt_loss = re.compile(r'(\d+(?:\.\d+)?)\s*%?\s*packet\s*loss', re.IGNORECASE)
        self._re_speed = re.compile(r'(\d+(?:\.\d+)?)\s*(?:Mbps|Gbps)', re.IGNORECASE)
        self._re_duplex = re.compile(r'(full|half)', re.IGNORECASE)
        self._re_kv_line = re.compile(r"name:\s*([^\s]+).*?status:\s*(up|down|disabled|error)", re.IGNORECASE)
        self._re_kv_ip = re.compile(r"ip:\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})", re.IGNORECASE)
    
    def parse(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse la sortie de la commande 'show system interface' de FortiGate
        
        Args:
            output: Sortie brute de la commande
            
        Returns:
            Liste des interfaces avec leurs informations
        """
        try:
            # Mode simplifié: détecter les interfaces au format key:value (ex: get system interface)
            kv_interfaces = self._parse_kv_interfaces(output)
            if kv_interfaces:
                self.logger.info(f"Parsing FortiGate (key:value) terminé: {len(kv_interfaces)} interfaces détectées")
                return kv_interfaces

            interfaces = []
            lines = output.split('\n')
            
            current_interface = None
            in_interface_block = False
            
            for line in lines:
                line = line.strip()
                
                # Ignorer les lignes vides et les commentaires
                if not line or line.startswith('#') or line.startswith('--'):
                    continue
                
                # Détecter le début d'un bloc d'interface
                if self._is_interface_header(line):
                    # Sauvegarder l'interface précédente si elle existe
                    if current_interface:
                        interfaces.append(current_interface)
                    
                    # Créer une nouvelle interface
                    current_interface = self._parse_interface_header(line)
                    in_interface_block = True
                    continue
                
                # Si nous sommes dans un bloc d'interface, parser les détails
                if in_interface_block and current_interface:
                    self._parse_interface_details(current_interface, line)
                    # FortiGate often uses key:value lines; detect name/status/link/admin
                    self._parse_key_value_status(current_interface, line)
            
            # Ajouter la dernière interface
            if current_interface:
                interfaces.append(current_interface)
            
            self.logger.info(f"Parsing FortiGate terminé: {len(interfaces)} interfaces détectées")
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing FortiGate: {str(e)}")
            return []
    
    def _is_interface_header(self, line: str) -> bool:
        """Détermine si une ligne est l'en-tête d'une interface"""
        # Patterns pour détecter les en-têtes d'interface FortiGate
        for pattern in self._re_interface_header:
            if pattern.match(line):
                return True
        
        return False
    
    def _parse_interface_header(self, line: str) -> Dict[str, Any]:
        """Parse l'en-tête d'une interface"""
        try:
            # Extraire le nom de l'interface et le statut
            parts = line.split()
            interface_name = parts[0]
            
            # Déterminer le statut
            status = 'unknown'
            if 'up' in line.lower():
                status = 'up'
            elif 'down' in line.lower():
                status = 'down'
            elif 'disabled' in line.lower():
                status = 'disabled'
            elif 'error' in line.lower():
                status = 'error'
            
            return {
                'name': interface_name,
                'status': status,
                'bandwidth_in': None,
                'bandwidth_out': None,
                'error_count': 0,
                'packet_loss': None,
                'ip_address': None,
                'mac_address': None,
                'raw_output': line,
                'details': {}
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing de l'en-tête d'interface: {str(e)}")
            return {
                'name': 'unknown',
                'status': 'unknown',
                'bandwidth_in': None,
                'bandwidth_out': None,
                'error_count': 0,
                'packet_loss': None,
                'ip_address': None,
                'mac_address': None,
                'raw_output': line,
                'details': {}
            }
    
    def _parse_interface_details(self, interface: Dict[str, Any], line: str):
        """Parse les détails d'une interface"""
        try:
            line_lower = line.lower()
            
            # Adresse IP
            ip_match = self._re_ip.search(line)
            if ip_match:
                interface['ip_address'] = ip_match.group(1)
            
            # Adresse MAC
            mac_match = self._re_mac.search(line)
            if mac_match:
                interface['mac_address'] = mac_match.group(1)
            
            # Bande passante
            bandwidth_match = self._re_bw.search(line)
            if bandwidth_match:
                value = float(bandwidth_match.group(1))
                unit = bandwidth_match.group(2)
                
                # Convertir en Mbps
                if 'Gbps' in unit:
                    value *= 1000
                elif 'Kbps' in unit:
                    value /= 1000
                
                if 'in' in line_lower or 'rx' in line_lower:
                    interface['bandwidth_in'] = value
                elif 'out' in line_lower or 'tx' in line_lower:
                    interface['bandwidth_out'] = value
            
            # Compteur d'erreurs
            error_match = self._re_errors.search(line_lower)
            if error_match:
                interface['error_count'] = int(error_match.group(1))
            
            # Perte de paquets
            packet_loss_match = self._re_pkt_loss.search(line_lower)
            if packet_loss_match:
                interface['packet_loss'] = float(packet_loss_match.group(1))
            
            # Mettre à jour la sortie brute
            interface['raw_output'] += '\n' + line
            
            # Stocker les détails supplémentaires
            if 'details' not in interface:
                interface['details'] = {}
            
            # Extraire d'autres informations utiles
            if 'mtu' in line_lower:
                mtu_match = re.search(r'(\d+)', line)
                if mtu_match:
                    interface['details']['mtu'] = int(mtu_match.group(1))
            
            if 'speed' in line_lower:
                speed_match = self._re_speed.search(line)
                if speed_match:
                    interface['details']['speed'] = speed_match.group(0)
            
            if 'duplex' in line_lower:
                duplex_match = self._re_duplex.search(line_lower)
                if duplex_match:
                    interface['details']['duplex'] = duplex_match.group(1)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing des détails d'interface: {str(e)}")

    def _parse_kv_interfaces(self, output: str) -> List[Dict[str, Any]]:
        """Parsing simplifié pour sorties FortiGate de type 'get system interface'.
        Extrait name, status, ip si présents sur la même ligne ou bloc proche.
        """
        try:
            interfaces: List[Dict[str, Any]] = []
            # Chercher lignes contenant 'name:' et 'status:'
            pattern = self._re_kv_line
            ip_pattern = self._re_kv_ip
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                m = pattern.search(line)
                if m:
                    name = m.group(1)
                    status = m.group(2).lower()
                    ip_match = ip_pattern.search(line)
                    ip_addr = ip_match.group(1) if ip_match else None
                    interfaces.append({
                        'name': name,
                        'status': status,
                        'bandwidth_in': None,
                        'bandwidth_out': None,
                        'error_count': 0,
                        'packet_loss': None,
                        'ip_address': ip_addr,
                        'mac_address': None,
                        'raw_output': line,
                        'details': {}
                    })
            return interfaces
        except Exception as e:
            self.logger.error(f"Erreur parsing key:value interfaces: {str(e)}")
            return []

    def _parse_key_value_status(self, interface: Dict[str, Any], line: str):
        """Parse les lignes FortiGate au format 'clé: valeur' pour statut explicite.
        Exemples typiques:
          - name: port1
          - status: up/down
          - link: up/down
          - admin: up/down
        """
        try:
            if ':' not in line:
                return
            key, value = [part.strip().lower() for part in line.split(':', 1)]

            if key in ('name', 'interface', 'ifname') and value:
                interface['name'] = value.split()[0]

            if key in ('status', 'state'):
                if 'down' in value:
                    interface['status'] = 'down'
                elif 'up' in value:
                    interface['status'] = 'up'
                elif 'error' in value:
                    interface['status'] = 'error'

            # Many FortiGate outputs expose link/admin separately; if either is down, consider down
            if key in ('link', 'admin'):
                if 'down' in value:
                    interface['status'] = 'down'

        except Exception as e:
            self.logger.error(f"Erreur lors du parsing key:value: {str(e)}")
    
    def parse_bandwidth_command(self, output: str) -> Dict[str, float]:
        """Parse la sortie de la commande de bande passante"""
        try:
            bandwidth_data = {}
            lines = output.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Chercher les informations de bande passante
                # Format: "port1 rx bytes: 1234567, tx bytes: 7654321"
                if 'bytes:' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface_name = parts[0]
                        
                        # Extraire les octets reçus et transmis
                        rx_match = re.search(r'rx\s+bytes:\s+(\d+)', line)
                        tx_match = re.search(r'tx\s+bytes:\s+(\d+)', line)
                        
                        if rx_match and tx_match:
                            rx_bytes = int(rx_match.group(1))
                            tx_bytes = int(tx_match.group(1))
                            
                            # Convertir en Mbps (approximatif)
                            bandwidth_data[interface_name] = {
                                'rx_mbps': round(rx_bytes * 8 / 1000000, 2),
                                'tx_mbps': round(tx_bytes * 8 / 1000000, 2)
                            }
            
            return bandwidth_data
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing de la bande passante: {str(e)}")
            return {}
    
    def parse_error_command(self, output: str) -> Dict[str, int]:
        """Parse la sortie de la commande de statistiques d'erreurs"""
        try:
            error_data = {}
            lines = output.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Chercher les informations d'erreurs
                # Format: "port1 rx errors: 5, tx errors: 2"
                if 'errors:' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface_name = parts[0]
                        
                        # Extraire les erreurs reçues et transmises
                        rx_errors_match = re.search(r'rx\s+errors:\s+(\d+)', line)
                        tx_errors_match = re.search(r'tx\s+errors:\s+(\d+)', line)
                        
                        if rx_errors_match and tx_errors_match:
                            rx_errors = int(rx_errors_match.group(1))
                            tx_errors = int(tx_errors_match.group(1))
                            
                            error_data[interface_name] = {
                                'rx_errors': rx_errors,
                                'tx_errors': tx_errors,
                                'total_errors': rx_errors + tx_errors
                            }
            
            return error_data
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing des erreurs: {str(e)}")
            return {}
    
    def get_interface_summary(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Retourne un résumé des interfaces"""
        try:
            total_interfaces = len(interfaces)
            up_interfaces = len([i for i in interfaces if i['status'] == 'up'])
            down_interfaces = len([i for i in interfaces if i['status'] == 'down'])
            error_interfaces = len([i for i in interfaces if i['status'] == 'error'])
            
            # Calculer la bande passante totale
            total_bandwidth_in = sum([i.get('bandwidth_in', 0) or 0 for i in interfaces])
            total_bandwidth_out = sum([i.get('bandwidth_out', 0) or 0 for i in interfaces])
            
            # Calculer le total des erreurs
            total_errors = sum([i.get('error_count', 0) for i in interfaces])
            
            return {
                'total_interfaces': total_interfaces,
                'up_interfaces': up_interfaces,
                'down_interfaces': down_interfaces,
                'error_interfaces': error_interfaces,
                'total_bandwidth_in': round(total_bandwidth_in, 2),
                'total_bandwidth_out': round(total_bandwidth_out, 2),
                'total_errors': total_errors,
                'health_percentage': round((up_interfaces / total_interfaces * 100) if total_interfaces > 0 else 0, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul du résumé: {str(e)}")
            return {
                'total_interfaces': 0,
                'up_interfaces': 0,
                'down_interfaces': 0,
                'error_interfaces': 0,
                'total_bandwidth_in': 0,
                'total_bandwidth_out': 0,
                'total_errors': 0,
                'health_percentage': 0
            }
