"""
Exécuteur SSH pour les commandes de daily check
"""

import logging
import time
import socket
import subprocess
import platform
import paramiko
from typing import List, Dict, Any, Optional
from auth_service.models import SSHUser

logger = logging.getLogger(__name__)

class SSHExecutor:
    """
    Classe pour exécuter des commandes SSH sur les firewalls
    """
    
    def __init__(self, connection_timeout: int = 3, command_timeout: int = 10, max_retries: int = 1):
        self.connection_timeout = connection_timeout
        self.command_timeout = command_timeout
        self.max_retries = max_retries
    
    def execute_commands_in_session(self, firewall, commands: List[str], user) -> List[Dict[str, Any]]:
        """
        Exécute une série de commandes dans une seule session SSH avec gestion d'erreur améliorée
        
        Args:
            firewall: Instance du modèle Firewall
            commands: Liste des commandes à exécuter
            user: Utilisateur qui exécute les commandes
            
        Returns:
            List[Dict]: Résultats des commandes
        """
        ssh = None
        channel = None
        
        try:
            # Test de ping rapide d'abord
            if not self._quick_ping_test(firewall.ip_address):
                logger.warning(f"Quick ping test failed for {firewall.ip_address}")
                # Essayer quand même le test SSH au cas où le ping serait bloqué
                if not self._test_network_connectivity(firewall.ip_address):
                    raise ConnectionError(f"Network unreachable: {firewall.ip_address}")
            
            # Récupérer l'utilisateur SSH
            ssh_user = SSHUser.objects.get(user=user)
            decrypted_password = ssh_user.get_ssh_password()

            # Établir la connexion SSH avec retry
            ssh = self._establish_ssh_connection(firewall, ssh_user, decrypted_password)
            
            if not ssh:
                raise ConnectionError(f"Failed to establish SSH connection to {firewall.ip_address}")

            results = []
            # Créer un canal interactif
            channel = ssh.invoke_shell()
            time.sleep(2)  # Attendre que le shell soit prêt

            # Exécuter chaque commande
            for cmd in commands:
                try:
                    logger.info(f"Executing command: {cmd}")
                    # Envoyer la commande
                    channel.send(cmd + '\n')
                    time.sleep(2)  # Attendre que la commande commence

                    # Lire la sortie complète avec timeout
                    output = self._read_output_with_timeout(channel)
                    logger.info(f"Command output length: {len(output)}")

                    # Nettoyer la sortie
                    cleaned_output = self._clean_output(output, cmd)

                    results.append({
                        'command': cmd,
                        'status': 'completed',
                        'output': cleaned_output,
                        'error': None
                    })

                except Exception as e:
                    logger.error(f"Error executing command {cmd}: {str(e)}")
                    results.append({
                        'command': cmd,
                        'status': 'failed',
                        'output': None,
                        'error': str(e)
                    })

            return results

        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            # Retourner des résultats d'erreur pour toutes les commandes
            error_results = []
            for cmd in commands:
                error_results.append({
                    'command': cmd,
                    'status': 'failed',
                    'output': None,
                    'error': f"Connection failed: {str(e)}"
                })
            return error_results
            
        finally:
            # Nettoyer les connexions
            if channel:
                try:
                    channel.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    def _test_network_connectivity(self, ip_address: str) -> bool:
        """
        Teste la connectivité réseau vers l'adresse IP avec timeout rapide
        
        Args:
            ip_address: Adresse IP à tester
            
        Returns:
            bool: True si connecté, False sinon
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # Timeout ultra-rapide à 1 seconde
            result = sock.connect_ex((ip_address, 22))
            sock.close()
            return result == 0
        except Exception as e:
            logger.warning(f"Network connectivity test failed for {ip_address}: {e}")
            return False
    
    def _quick_ping_test(self, ip_address: str) -> bool:
        """
        Test de ping rapide pour détecter rapidement les problèmes de connectivité
        
        Args:
            ip_address: Adresse IP à tester
            
        Returns:
            bool: True si ping réussi, False sinon
        """
        try:
            # Déterminer la commande ping selon l'OS
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "500", ip_address]  # 500ms timeout sur Windows
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip_address]  # 1 seconde timeout sur Linux/Mac
            
            # Exécuter le ping avec timeout ultra-court
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=1  # Timeout global de 1 seconde
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Ping test failed for {ip_address}: {e}")
            return False
    
    def _establish_ssh_connection(self, firewall, ssh_user, password) -> Optional[paramiko.SSHClient]:
        """
        Établit une connexion SSH avec retry
        
        Args:
            firewall: Instance du modèle Firewall
            ssh_user: Utilisateur SSH
            password: Mot de passe déchiffré
            
        Returns:
            paramiko.SSHClient ou None si échec
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"SSH connection attempt {attempt + 1}/{self.max_retries} to {firewall.ip_address}")
                
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                ssh.connect(
                    firewall.ip_address,
                    username=ssh_user.ssh_username,
                    password=password,
                    timeout=self.connection_timeout,
                    banner_timeout=2,  # Timeout ultra-rapide pour banner
                    auth_timeout=2     # Timeout ultra-rapide pour authentification
                )
                
                logger.info(f"SSH connection established to {firewall.ip_address}")
                return ssh
                
            except (paramiko.AuthenticationException, paramiko.SSHException) as e:
                logger.error(f"SSH authentication/connection error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)  # Backoff rapide de 1 seconde
                
            except socket.timeout as e:
                logger.error(f"SSH connection timeout (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)  # Backoff rapide de 1 seconde
                
            except Exception as e:
                logger.error(f"Unexpected SSH error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)  # Backoff rapide de 1 seconde
        
        return None
    
    def _read_output_with_timeout(self, channel) -> str:
        """
        Lit la sortie complète d'une commande avec timeout amélioré
        
        Args:
            channel: Canal SSH
            
        Returns:
            str: Sortie de la commande
        """
        output = ""
        start_time = time.time()
        last_data_time = start_time
        max_idle_time = 3  # Maximum 3 secondes sans données pour détection ultra-rapide
        
        while True:
            current_time = time.time()
            
            # Vérifier le timeout global
            if current_time - start_time > self.command_timeout:
                logger.warning(f"Global timeout reached while reading command output")
                break
            
            # Vérifier si le canal est prêt à être lu
            if channel.recv_ready():
                try:
                    chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    last_data_time = current_time
                    
                    # Détecter le prompt final
                    if '#' in chunk or '>' in chunk:
                        time.sleep(1)  # Attendre un peu plus pour être sûr
                        if not channel.recv_ready():
                            break
                    elif '--More--' in chunk:
                        # Envoyer un espace pour paginer
                        channel.send(' ')
                        # Supprimer --More-- de la sortie capturée
                        output = output.replace('--More--', '')
                        time.sleep(1)
                        
                except Exception as e:
                    logger.warning(f"Error reading from channel: {e}")
                    break
            else:
                # Vérifier le timeout d'inactivité
                if current_time - last_data_time > max_idle_time:
                    logger.warning(f"Idle timeout reached while reading command output")
                    break
                time.sleep(0.1)
        
        return output
    
    def _clean_output(self, output: str, command: str) -> str:
        """
        Nettoie la sortie d'une commande
        
        Args:
            output: Sortie brute
            command: Commande exécutée
            
        Returns:
            str: Sortie nettoyée
        """
        # Supprimer la commande elle-même de la sortie et les prompts résiduels
        output_lines = output.split('\n')
        cleaned_output_lines = []
        
        for line in output_lines:
            # Ignorer les lignes qui contiennent uniquement la commande ou le prompt
            if line.strip() != command.strip() and not line.strip().endswith(tuple(['#', '>'])):
                cleaned_output_lines.append(line)
        
        return '\n'.join(cleaned_output_lines).strip()
