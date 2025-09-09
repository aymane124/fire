import asyncio
import time
import paramiko
import logging
from auth_service.models import SSHUser
from auth_service.utils.crypto import decrypt_ssh_data


logger = logging.getLogger(__name__)


class SimpleSSHSession:
    """SSH session helper using Paramiko directly (no websocket dependency).

    - Maintains a single interactive shell channel to support multiple sequential commands
    - Uses event loop executors to avoid blocking the async loop
    """

    def __init__(self, firewall):
        self.firewall = firewall
        self.ssh_client = None
        self.ssh_channel = None
        self.connected = False

    async def connect(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._connect_sync)
        self.connected = True

    def _connect_sync(self):
        try:
            username = getattr(self.firewall, 'ssh_user', None)
            password = getattr(self.firewall, 'ssh_password', None)
            port = getattr(self.firewall, 'ssh_port', 22) or 22

            # Fallback to stored SSHUser credentials if firewall creds are missing
            if not username or not password:
                try:
                    owner = getattr(self.firewall, 'owner', None)
                    ssh_user_obj = None
                    if owner:
                        ssh_user_obj = SSHUser.objects.filter(user=owner).first()
                    if not ssh_user_obj:
                        ssh_user_obj = SSHUser.objects.first()
                    if ssh_user_obj:
                        username = ssh_user_obj.ssh_username
                        try:
                            password = decrypt_ssh_data(ssh_user_obj.ssh_password)
                        except Exception:
                            password = ssh_user_obj.ssh_password
                except Exception as cred_err:
                    logger.error(f"SSH credentials fallback error: {str(cred_err)}")

            # Defaults if still missing
            username = username or 'admin'
            password = password or ''

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                self.firewall.ip_address,
                port=port,
                username=username,
                password=password,
                timeout=10
            )

            channel = client.invoke_shell()
            channel.settimeout(1)

            self.ssh_client = client
            self.ssh_channel = channel

        except Exception as e:
            logger.error(f"SimpleSSH connect error: {str(e)}")
            raise

    async def execute_command(self, command: str, command_id: str, timeout: float = 10.0) -> str:
        if not self.connected or not self.ssh_channel:
            raise RuntimeError("SSH not connected")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._exec_sync, command, timeout)

    def _exec_sync(self, command: str, timeout: float) -> str:
        try:
            self.ssh_channel.send(command + '\n')
            start = time.time()
            output = ''
            prompts = ['# ', '$ ', '> ', 'FortiGate #', 'Router#', 'Switch#']
            while time.time() - start < timeout:
                if self.ssh_channel.recv_ready():
                    chunk = self.ssh_channel.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    if any(p in output for p in prompts):
                        break
                else:
                    time.sleep(0.1)
            return output
        except Exception as e:
            logger.error(f"SimpleSSH exec error: {str(e)}")
            raise

    async def disconnect(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._disconnect_sync)
        self.connected = False

    def _disconnect_sync(self):
        try:
            if self.ssh_channel:
                self.ssh_channel.close()
            if self.ssh_client:
                self.ssh_client.close()
        except Exception as e:
            logger.error(f"SimpleSSH disconnect error: {str(e)}")


