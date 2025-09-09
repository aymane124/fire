#!/usr/bin/env python
import asyncio
import paramiko
import logging
from websocket_service.models import TerminalSession, TerminalCommand
from auth_service.models import SSHUser
from auth_service.utils.crypto import decrypt_ssh_data
from django.utils import timezone

logger = logging.getLogger(__name__)

class SSHSessionManager:
    """Gestionnaire de session SSH interactive"""
    
    def __init__(self, firewall, admin_user):
        self.firewall = firewall
        self.admin_user = admin_user
        self.ssh_client = None
        self.ssh_channel = None
        self.session = None
        self.is_connected = False
        
    async def connect(self):
        """Établir une connexion SSH"""
        try:
            # Créer une session terminal
            session_id = f"ssh_session_{int(timezone.now().timestamp())}"
            self.session = await self._create_session(session_id)
            
            # Établir la connexion SSH
            await self._connect_ssh()
            
            self.is_connected = True
            
        except Exception as e:
            logger.error(f"Erreur de connexion: {str(e)}")
            raise e
    
    async def _connect_ssh(self):
        """Établir la connexion SSH"""
        try:
            # Récupérer les identifiants SSH
            ssh_credentials = await self._get_ssh_credentials()
            ssh_user = ssh_credentials.ssh_username
            ssh_password = decrypt_ssh_data(ssh_credentials.ssh_password)
            ssh_port = getattr(self.firewall, 'ssh_port', 22)
            
            # Créer la connexion SSH
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Se connecter
            self.ssh_client.connect(
                self.firewall.ip_address,
                port=ssh_port,
                username=ssh_user,
                password=ssh_password,
                timeout=10
            )
            # Keepalive pour éviter les coupures
            try:
                transport = self.ssh_client.get_transport()
                if transport:
                    transport.set_keepalive(30)
            except Exception:
                pass
            
            # Créer un canal shell interactif avec PTY pour des invites stables
            self.ssh_channel = self.ssh_client.invoke_shell(term='vt100', width=200, height=60)
            self.ssh_channel.settimeout(1)
            
            # Drainer la bannière/avertissements initiaux jusqu'à l'invite
            try:
                await self._read_output(timeout=2)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Erreur SSH: {str(e)}")
            raise e
    
    async def execute_command(self, command, command_id, timeout: float = 15.0):
        """Exécuter une commande dans la session interactive"""
        try:
            if not self.is_connected or not self.ssh_channel:
                raise Exception("Connexion SSH non établie")
            
            # Envoyer la commande
            self.ssh_channel.send(command + '\n')
            
            # Attendre et récupérer la sortie
            output = await self._read_output(timeout=timeout)
            
            # Mettre à jour la commande en base
            await self._update_command_status(command_id, 'completed', output)
            
            return output
            
        except Exception as e:
            logger.error(f"Erreur d'exécution: {str(e)}")
            await self._update_command_status(command_id, 'failed', str(e))
            raise e
    
    async def _read_output(self, timeout: float = 10.0):
        """Lire la sortie de la commande"""
        import time
        start_time = time.time()
        output = ""
        last_len = 0
        last_change = start_time
        idle_break_ms = 0.25  # 250ms d'inactivité après invite -> sortie
        
        while time.time() - start_time < timeout:
            if self.ssh_channel.recv_ready():
                chunk = self.ssh_channel.recv(65536).decode('utf-8', errors='ignore')
                output += chunk
                
                # Vérifier si la commande est terminée (prompt visible)
                if self._is_command_complete(output):
                    # si le buffer n'évolue plus pendant un court instant, on sort
                    if len(output) != last_len:
                        last_len = len(output)
                        last_change = time.time()
                    elif time.time() - last_change >= idle_break_ms:
                        break
            else:
                await asyncio.sleep(0.03)
        
        return output
    
    def _is_command_complete(self, output):
        """Vérifier si la commande est terminée"""
        prompts = ['# ', '$ ', '> ', 'FortiGate #', 'FortiGate-VMX #', '(global) #', 'Router#', 'Switch#']
        return any(prompt in output for prompt in prompts)
    
    async def _update_command_status(self, command_id, status, output):
        """Mettre à jour le statut de la commande"""
        try:
            command = await self._get_command_by_id(command_id)
            command.status = status
            command.output = output
            command.completed_at = timezone.now()
            await self._save_command(command)
        except Exception as e:
            logger.error(f"Erreur mise à jour commande: {str(e)}")
    
    async def disconnect(self):
        """Fermer la connexion"""
        try:
            if self.ssh_channel:
                self.ssh_channel.close()
            if self.ssh_client:
                self.ssh_client.close()
            if self.session:
                self.session.is_active = False
                await self._save_session(self.session)
            
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Erreur fermeture: {str(e)}")
    
    # Méthodes helper avec sync_to_async
    async def _create_session(self, session_id):
        """Créer une session terminal de manière asynchrone"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(TerminalSession.objects.create)(
            user=self.admin_user,
            firewall=self.firewall,
            session_id=session_id,
            is_active=True
        )
    
    async def _get_ssh_credentials(self):
        """Récupérer les identifiants SSH de manière asynchrone"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(SSHUser.objects.get)(user=self.admin_user)
    
    async def _get_command_by_id(self, command_id):
        """Récupérer une commande par ID de manière asynchrone"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(TerminalCommand.objects.get)(command_id=command_id)
    
    async def _save_command(self, command):
        """Sauvegarder une commande de manière asynchrone"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(command.save)()
    
    async def _save_session(self, session):
        """Sauvegarder une session de manière asynchrone"""
        from asgiref.sync import sync_to_async
        return await sync_to_async(session.save)()

# Instance globale pour maintenir la connexion
_ssh_sessions = {}

async def get_or_create_ssh_session(firewall, admin_user):
    """Obtenir ou créer une session SSH"""
    key = f"{firewall.id}_{admin_user.id}"
    
    if key not in _ssh_sessions:
        session = SSHSessionManager(firewall, admin_user)
        await session.connect()
        _ssh_sessions[key] = session
    else:
        session = _ssh_sessions[key]
    
    return session

async def execute_command_via_ssh(firewall, command, command_id, admin_user):
    """Exécuter une commande via SSH"""
    session = await get_or_create_ssh_session(firewall, admin_user)
    return await session.execute_command(command, command_id)
