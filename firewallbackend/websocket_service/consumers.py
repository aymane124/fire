import json
import asyncio
import paramiko
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from firewall_service.models import Firewall
from auth_service.models import SSHUser
from .models import TerminalSession, TerminalCommand
import uuid
from . import config
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)


class TerminalConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firewall_id = None
        self.user = None
        self.ssh_client = None
        self.ssh_channel = None
        self.session = None
        self.room_group_name = None
        self.command_lock = asyncio.Lock()
        self.is_command_executing = False
        self.last_completion_time = 0
        self._output_buffer = []
        self._last_flush_monotonic = 0.0
        self._last_output_monotonic = 0.0
        self._command_output_accumulator = []

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            self.firewall_id = self.scope['url_route']['kwargs']['firewall_id']
            self.user = self.scope.get('user')
            
            if not self.user:
                await self.close(code=4001)
                return

            firewall = await self.get_firewall()
            if not firewall:
                await self.close(code=4002)
                return

            self.room_group_name = f'terminal_{self.firewall_id}_{self.user.id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.create_terminal_session(firewall)
            await self.accept()

            await self.send_message('system', f'Terminal connecté au pare-feu {firewall.name} ({firewall.ip_address})')

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            await self.close_ssh_connection()
            if self.session:
                await self.update_session_status(False)
            if self.room_group_name:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'command':
                command = data.get('command', '').strip()
                if command and not self.is_command_executing:
                    await self.execute_command(command)
            elif message_type == 'connect_ssh':
                await self.connect_ssh()
            elif message_type == 'disconnect_ssh':
                await self.close_ssh_connection()
            elif message_type == 'pager_action':
                action = data.get('action')  # 'page' | 'line' | 'quit'
                if self.ssh_channel and action in ('page', 'line', 'quit'):
                    key = ' ' if action == 'page' else ('\n' if action == 'line' else 'q')
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None, lambda: self.ssh_channel.send(key)
                        )
                    except Exception:
                        pass

        except json.JSONDecodeError:
            await self.send_message('error', 'Message invalide')
        except Exception as e:
            logger.error(f"Receive error: {str(e)}")
            await self.send_message('error', f'Erreur: {str(e)}')

    async def send_message(self, message_type, content):
        """Send message to client"""
        await self.send(text_data=json.dumps({
            'type': message_type,
            'content': content
        }))

    @database_sync_to_async
    def get_firewall(self):
        """Get firewall from database"""
        try:
            return Firewall.objects.get(id=self.firewall_id)
        except Firewall.DoesNotExist:
            return None

    @database_sync_to_async
    def create_terminal_session(self, firewall):
        """Create terminal session in database"""
        try:
            session_id = str(uuid.uuid4())
            self.session = TerminalSession.objects.create(
                user=self.user,
                firewall=firewall,
                session_id=session_id,
                is_active=True
            )
            return self.session
        except Exception as e:
            logger.error(f"Session creation error: {str(e)}")
            return None

    @database_sync_to_async
    def update_session_status(self, is_active):
        """Update session status"""
        if self.session:
            self.session.is_active = is_active
            self.session.save()

    @database_sync_to_async
    def get_ssh_credentials(self):
        """Get SSH credentials for current user"""
        try:
            ssh_user = SSHUser.objects.get(user=self.user)
            return {
                'username': ssh_user.ssh_username,
                'password': ssh_user.get_ssh_password()
            }
        except SSHUser.DoesNotExist:
            return None

    async def connect_ssh(self):
        """Establish SSH connection to firewall"""
        try:
            await self.send_message('system', 'Connexion SSH en cours...')

            ssh_credentials = await self.get_ssh_credentials()
            if not ssh_credentials:
                await self.send_message('error', 'Identifiants SSH non trouvés')
                return

            firewall = await self.get_firewall()
            if not firewall:
                await self.send_message('error', 'Pare-feu non trouvé')
                return

            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to firewall
            def ssh_connect():
                return self.ssh_client.connect(
                    firewall.ip_address,
                    22,
                    ssh_credentials['username'],
                    ssh_credentials['password'],
                    timeout=config.SSH_TIMEOUT,
                )

            await asyncio.get_event_loop().run_in_executor(None, ssh_connect)

            # Create shell channel
            def create_shell():
                channel = self.ssh_client.invoke_shell()
                channel.settimeout(1)
                return channel

            self.ssh_channel = await asyncio.get_event_loop().run_in_executor(None, create_shell)

            await self.send_message('system', 'Connexion SSH établie avec succès')
            asyncio.create_task(self.read_ssh_output())

        except Exception as e:
            logger.error(f"SSH connection error: {str(e)}")
            await self.send_message('error', f'Erreur de connexion SSH: {str(e)}')

    async def execute_command(self, command):
        """Execute command on firewall via SSH"""
        async with self.command_lock:
            try:
                if not self.ssh_channel:
                    await self.send_message('error', 'Connexion SSH non établie')
                    return

                self.is_command_executing = True
                # Notify UI explicitly
                await self.send(text_data=json.dumps({
                    'type': 'command_status',
                    'status': 'executing',
                    'command': command,
                }))

                # Save command to database
                await self.save_command(command)

                # Send command
                def send_command():
                    return self.ssh_channel.send(command + '\n')

                await asyncio.get_event_loop().run_in_executor(None, send_command)

                # Set completion timeout
                asyncio.create_task(self.command_completion_timeout())

            except Exception as e:
                logger.error(f"Command execution error: {str(e)}")
                await self.send_message('error', f'Erreur d\'exécution: {str(e)}')
                self.is_command_executing = False

    async def execute_command_message(self, event):
        """Handle execute_command messages from channel layer (for automated emails)"""
        try:
            command = event.get('command', '')
            command_id = event.get('command_id', '')
            session_id = event.get('session_id', '')
            
            logger.info(f"📥 [WEBSOCKET] Received execute_command message: {command} (ID: {command_id})")
            
            # Connect SSH if not already connected
            if not self.ssh_channel:
                await self.connect_ssh()
                if not self.ssh_channel:
                    await self.update_command_status(command_id, 'failed', 'Connexion SSH échouée')
                    return
            
            # Execute the command
            await self.execute_command_for_email(command, command_id)
            
        except Exception as e:
            logger.error(f"❌ [WEBSOCKET] Error in execute_command_message: {str(e)}")
            command_id = event.get('command_id', '')
            await self.update_command_status(command_id, 'failed', str(e))

    async def execute_command_for_email(self, command, command_id):
        """Execute command specifically for email automation"""
        try:
            logger.info(f"💻 [WEBSOCKET] Executing command for email: {command}")
            
            # Update command status to executing
            await self.update_command_status(command_id, 'executing', '')
            
            # Send command via SSH
            def send_command():
                return self.ssh_channel.send(command + '\n')
            
            await asyncio.get_event_loop().run_in_executor(None, send_command)
            
            # Wait for command completion with timeout
            await self.wait_for_command_completion(command_id)
            
        except Exception as e:
            logger.error(f"❌ [WEBSOCKET] Error executing command for email: {str(e)}")
            await self.update_command_status(command_id, 'failed', str(e))

    async def wait_for_command_completion(self, command_id, timeout=30):
        """Wait for command completion with timeout"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if command is completed
            command = await self.get_command_by_id(command_id)
            if command and command.status in ['completed', 'failed']:
                logger.info(f"✅ [WEBSOCKET] Command {command_id} completed with status: {command.status}")
                return
            
            await asyncio.sleep(1)
        
        # Timeout reached
        logger.warning(f"⚠️ [WEBSOCKET] Command {command_id} timed out after {timeout}s")
        await self.update_command_status(command_id, 'failed', 'Timeout atteint')

    @database_sync_to_async
    def update_command_status(self, command_id, status, output=''):
        """Update command status in database"""
        try:
            command = TerminalCommand.objects.get(command_id=command_id)
            command.status = status
            if output:
                command.output = output
            command.completed_at = timezone.now()
            command.save()
            logger.info(f"📝 [WEBSOCKET] Updated command {command_id} status to {status}")
        except TerminalCommand.DoesNotExist:
            logger.error(f"❌ [WEBSOCKET] Command {command_id} not found")
        except Exception as e:
            logger.error(f"❌ [WEBSOCKET] Error updating command status: {str(e)}")

    @database_sync_to_async
    def get_command_by_id(self, command_id):
        """Get command by ID from database"""
        try:
            return TerminalCommand.objects.get(command_id=command_id)
        except TerminalCommand.DoesNotExist:
            return None

    async def read_ssh_output(self):
        """Read SSH output and send to client with throttled flushes for large results"""
        try:
            self._last_flush_monotonic = asyncio.get_event_loop().time()
            while self.ssh_channel and not self.ssh_channel.closed:
                if self.ssh_channel.recv_ready():
                    try:
                        output_bytes = self.ssh_channel.recv(config.SSH_BUFFER_SIZE)
                    except Exception:
                        output_bytes = b''
                    output = output_bytes.decode('utf-8', errors='ignore')
                    if output:
                        self._last_output_monotonic = asyncio.get_event_loop().time()
                        # Handle FortiGate pager prompts
                        if '--More--' in output:
                            # Remove pager indicator from what we display
                            output = output.replace('--More--', '')
                            mode = getattr(config, 'PAGER_MODE', 'page')
                            if mode == 'page':
                                key = ' '
                            elif mode == 'line':
                                key = '\n'
                            elif mode == 'manual':
                                key = None
                                # Inform frontend pager is waiting
                                await self.send(text_data=json.dumps({
                                    'type': 'pager',
                                    'status': 'more'
                                }))
                            else:
                                key = ' '

                            if key is not None:
                                try:
                                    await asyncio.get_event_loop().run_in_executor(
                                        None, lambda: self.ssh_channel.send(key)
                                    )
                                except Exception:
                                    pass
                    if output:
                        cleaned = self._clean_output(output)
                        if cleaned:
                            self._output_buffer.append(cleaned)

                        # Check for command completion markers on the raw chunk
                        if self.is_command_executing and self.is_command_complete(output):
                            await self.handle_command_completion()

                # Flush buffered output at controlled interval
                now = asyncio.get_event_loop().time()
                if self._output_buffer and (now - self._last_flush_monotonic) >= config.OUTPUT_FLUSH_INTERVAL:
                    combined = ''.join(self._output_buffer)
                    self._output_buffer.clear()

                    # Always send output immediately for better responsiveness
                    if combined.strip():
                        # If extremely large, send in slices
                        start_index = 0
                        total_len = len(combined)
                        while start_index < total_len:
                            end_index = min(start_index + config.OUTPUT_MAX_CHUNK_SIZE, total_len)
                            chunk = combined[start_index:end_index]
                            await self.send_message('output', chunk)
                            start_index = end_index

                    self._last_flush_monotonic = now

                # Inactivity-based completion when executing a command
                if self.is_command_executing:
                    # If we never received output since start, _last_output_monotonic could be 0
                    last_out = self._last_output_monotonic or self._last_flush_monotonic
                    if (now - last_out) >= config.QUIET_COMPLETION_WINDOW:
                        await self.handle_command_completion()

                await asyncio.sleep(config.OUTPUT_POLLING_INTERVAL)

        except Exception as e:
            logger.error(f"SSH output reading error: {str(e)}")

    def is_command_complete(self, output):
        """Check if command execution is complete"""
        # Check for FortiGate prompt patterns
        prompt_patterns = [
            'FortiGate-VMX #',
            'FortiGate #',
            'C:>',
            '# '
        ]
        
        for pattern in prompt_patterns:
            if pattern in output:
                return True
        return False

    async def handle_command_completion(self):
        """Handle command completion"""
        current_time = asyncio.get_event_loop().time()
        
        # Prevent multiple completion messages within 1 second
        if current_time - self.last_completion_time > 1.0:
            self.is_command_executing = False
            self.last_completion_time = current_time
            
            # Get the latest command and update its status
            latest_command = await self.get_latest_executing_command()
            if latest_command:
                # Collect all output from buffer
                output = ''.join(self._output_buffer)
                self._output_buffer.clear()
                
                # Update command status with collected output
                await self.update_command_status(latest_command.command_id, 'completed', output)
                logger.info(f"✅ [WEBSOCKET] Command {latest_command.command_id} completed with output length: {len(output)}")
            
            # Notify UI explicitly
            await self.send(text_data=json.dumps({
                'type': 'command_status',
                'status': 'completed',
            }))

    @database_sync_to_async
    def get_latest_executing_command(self):
        """Get the latest executing command from database"""
        try:
            if self.session:
                return self.session.commands.filter(status='executing').order_by('-created_at').first()
            return None
        except Exception as e:
            logger.error(f"Error getting latest executing command: {str(e)}")
            return None

    async def command_completion_timeout(self):
        """Timeout for command completion"""
        await asyncio.sleep(config.COMMAND_TIMEOUT)
        if self.is_command_executing:
            self.is_command_executing = False
            await self.send(text_data=json.dumps({
                'type': 'command_status',
                'status': 'completed',
                'reason': 'timeout',
            }))

    async def close_ssh_connection(self):
        """Close SSH connection"""
        try:
            if self.ssh_channel:
                self.ssh_channel.close()
                self.ssh_channel = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
                
            self.is_command_executing = False
            self._output_buffer.clear()
            
        except Exception as e:
            logger.error(f"SSH close error: {str(e)}")

    def _clean_output(self, text: str) -> str:
        """Remove unwanted control characters and normalize newlines."""
        if not text:
            return text
        # Remove carriage returns used for progress updates
        text = text.replace('\r', '')
        # Replace any stray nulls
        text = text.replace('\x00', '')
        # Remove backspaces
        text = text.replace('\x08', '')
        # Strip common ANSI escape sequences
        try:
            import re
            ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
            text = ansi_escape.sub('', text)
            # Remove various forms of pager markers
            pager_pattern = re.compile(r"--More--\s*", re.IGNORECASE)
            text = pager_pattern.sub('', text)
        except Exception:
            pass
        return text

    @database_sync_to_async
    def save_command(self, command):
        """Save command to database"""
        try:
            return TerminalCommand.objects.create(
                session=self.session,
                command=command,
                command_id=str(uuid.uuid4()),
                status='executing'
            )
        except Exception as e:
            logger.error(f"Command save error: {str(e)}")
            return None
