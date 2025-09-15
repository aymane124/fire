from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from auth_service.models import SSHUser
from .models import FirewallCommand
from .serializers import FirewallCommandSerializer, FirewallCommandExecuteSerializer, FirewallConfigSaveSerializer
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.conf import settings
import os
import paramiko
from datetime import datetime
from firewall_service.models import Firewall
import time
from rest_framework.views import APIView
import re
from auth_service.utils.crypto import decrypt_ssh_data
import logging
import base64
import threading
from queue import Queue
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queue pour stocker les tâches en cours
config_task_queue = Queue()
# Dictionnaire pour stocker l'état des tâches
config_task_status = {}
# Lock pour la mise à jour du statut
status_lock = Lock()

def process_single_firewall(firewall, command, ssh_user, decrypted_password, base_config_dir, task_id):
    try:
        # Établir la connexion SSH avec des paramètres optimisés
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            firewall.ip_address,
            username=ssh_user.ssh_username,
            password=decrypted_password,
            timeout=2,  # Timeout réduit
            banner_timeout=1,
            auth_timeout=1
        )
        
        # Exécuter la commande directement sans shell
        stdin, stdout, stderr = ssh.exec_command(command, timeout=5)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        if error:
            raise Exception(f"Command error: {error}")
        
        # Nettoyer la sortie rapidement
        output = '\n'.join(line for line in output.split('\n')
                        if (line.strip() != command.strip() and 
                            not line.strip().endswith(tuple(['#', '>'])) and
                            not line.strip().startswith('--More--')))
        
        # Sauvegarder le fichier
        if firewall.data_center and firewall.firewall_type:
            dc_dir = os.path.join(base_config_dir, firewall.data_center.name)
            os.makedirs(dc_dir, exist_ok=True)
            
            fw_type_dir = os.path.join(dc_dir, firewall.firewall_type.name)
            os.makedirs(fw_type_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{firewall.name}_{timestamp}.txt'
            filepath = os.path.join(fw_type_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(output)
        
        # Créer l'enregistrement
        command_result = FirewallCommand.objects.create(
            firewall=firewall,
            user=ssh_user.user,
            command=command,
            status='completed',
            output=output
        )
        
        return {
            'firewall_id': firewall.id,
            'firewall_name': firewall.name,
            'status': 'success',
            'output': output,
            'filepath': filepath if firewall.data_center and firewall.firewall_type else None
        }
        
    except Exception as e:
        logger.error(f"Error processing firewall {firewall.id}: {str(e)}")
        return {
            'firewall_id': firewall.id,
            'firewall_name': firewall.name,
            'status': 'failed',
            'error': str(e)
        }
    finally:
        if 'ssh' in locals():
            ssh.close()

def config_background_worker():
    while True:
        try:
            task = config_task_queue.get()
            if task is None:
                break
                
            task_id = task['task_id']
            with status_lock:
                config_task_status[task_id] = {
                    'status': 'running',
                    'progress': 0,
                    'message': 'Starting configuration save...',
                    'last_update': time.time()
                }
            
            try:
                firewalls = task['firewalls']
                command = task['command']
                user = task['user']
                
                total_firewalls = len(firewalls)
                processed_firewalls = 0
                results = []
                
                # Créer le répertoire de base pour les configurations
                documents_path = os.path.expanduser('~/Documents')
                base_config_dir = os.path.join(documents_path, 'FirewallConfigs')
                os.makedirs(base_config_dir, exist_ok=True)
                
                # Récupérer les informations SSH une seule fois
                ssh_user = SSHUser.objects.get(user=user)
                decrypted_password = ssh_user.get_ssh_password()
                
                # Utiliser ThreadPoolExecutor pour le traitement parallèle
                with ThreadPoolExecutor(max_workers=min(10, total_firewalls)) as executor:
                    # Soumettre toutes les tâches
                    future_to_firewall = {
                        executor.submit(
                            process_single_firewall,
                            firewall,
                            command,
                            ssh_user,
                            decrypted_password,
                            base_config_dir,
                            task_id
                        ): firewall for firewall in firewalls
                    }
                    
                    # Traiter les résultats au fur et à mesure qu'ils arrivent
                    for future in as_completed(future_to_firewall):
                        firewall = future_to_firewall[future]
                        try:
                            result = future.result()
                            results.append(result)
                            processed_firewalls += 1
                            
                            # Mettre à jour la progression toutes les 2 secondes seulement
                            current_time = time.time()
                            with status_lock:
                                if current_time - config_task_status[task_id]['last_update'] >= 2:
                                    config_task_status[task_id].update({
                                        'progress': int((processed_firewalls / total_firewalls) * 100),
                                        'message': f'Processed {processed_firewalls}/{total_firewalls} firewalls',
                                        'last_update': current_time
                                    })
                        except Exception as e:
                            logger.error(f"Error processing result for firewall {firewall.id}: {str(e)}")
                
                with status_lock:
                    config_task_status[task_id].update({
                        'status': 'completed',
                        'progress': 100,
                        'message': 'All configurations saved',
                        'results': results,
                        'last_update': time.time()
                    })
                
            except Exception as e:
                logger.error(f"Error in background task: {str(e)}")
                with status_lock:
                    config_task_status[task_id].update({
                        'status': 'failed',
                        'message': str(e),
                        'last_update': time.time()
                    })
            
            finally:
                config_task_queue.task_done()
                
        except Exception as e:
            logger.error(f"Error in worker thread: {str(e)}")
            continue

# Démarrer le worker thread
config_worker_thread = threading.Thread(target=config_background_worker, daemon=True)
config_worker_thread.start()

# Create your views here.

class FirewallCommandViewSet(viewsets.ModelViewSet):
    queryset = FirewallCommand.objects.all()
    serializer_class = FirewallCommandSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = FirewallCommand.objects.all()
        firewall_id = self.request.query_params.get('firewall_id')
        if firewall_id:
            try:
                # Essayer de convertir en UUID si ce n'est pas déjà le cas
                if not isinstance(firewall_id, str) or len(firewall_id) != 36:
                    # Si c'est un ID numérique, récupérer le pare-feu et utiliser son UUID
                    firewall = Firewall.objects.get(id=firewall_id)
                    firewall_id = str(firewall.id)
                queryset = queryset.filter(firewall_id=firewall_id)
            except (ValueError, Firewall.DoesNotExist) as e:
                logger.error(f"Invalid firewall_id: {firewall_id}. Error: {str(e)}")
                return FirewallCommand.objects.none()
        return queryset.select_related('firewall')

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f"Command created for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f"Command updated for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f"Command deleted for firewall {instance.firewall.name}",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        firewall_id = request.data.get('firewall_id')
        command = request.data.get('command')
        parameters = request.data.get('parameters', {})

        if not firewall_id or not command:
            return Response(
                {'error': 'firewall_id et command sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            firewall = Firewall.objects.get(id=firewall_id)
            if not firewall.ip_address:
                return Response(
                    {'error': f"Le pare-feu {firewall.name} n'a pas d'adresse IP configurée"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Firewall.DoesNotExist:
            return Response(
                {'error': 'Pare-feu non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Initialiser les paramètres avec les informations de base
        initial_parameters = {
            'firewall_info': {
                'id': str(firewall.id),
                'name': firewall.name,
                'ip_address': firewall.ip_address,
                'model': firewall.model,
                'version': firewall.version
            },
            'command_info': {
                'raw_command': command,
                'timestamp': datetime.now().isoformat(),
                'user': {
                    'id': str(request.user.id),
                    'username': request.user.username
                }
            },
            'status_info': {
                'initial_status': 'pending',
                'created_at': datetime.now().isoformat()
            }
        }

        # Fusionner avec les paramètres fournis par l'utilisateur
        if parameters:
            initial_parameters.update(parameters)

        command_obj = FirewallCommand.objects.create(
            firewall=firewall,
            user=request.user,
            command=command,
            parameters=initial_parameters,
            status='pending'
        )

        serializer = self.get_serializer(command_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _execute_command_async(self, command_obj, firewall):
        try:
            command_obj.status = 'executing'
            command_obj.save()
            command_obj.add_to_history(
                action='execute_start',
                status='executing',
                details=f"Starting command execution on {firewall.name}\nCommand: {command_obj.command}",
                user=command_obj.user,
                ip_address=None
            )

            # Récupérer l'utilisateur SSH
            ssh_user = SSHUser.objects.get(user=command_obj.user)
            logger.info(f"Retrieved SSH user: {ssh_user.ssh_username}")
            
            # Déchiffrer le mot de passe SSH
            try:
                logger.info(f"Attempting to decrypt SSH password for user: {ssh_user.ssh_username}")
                decrypted_password = ssh_user.get_ssh_password()
                logger.info("SSH password decrypted successfully")
            except Exception as e:
                logger.error(f"Error decrypting SSH password: {str(e)}")
                command_obj.status = 'failed'
                command_obj.error_message = f'Error decrypting SSH password: {str(e)}'
                command_obj.save()
                command_obj.add_to_history(
                    action='execute_error',
                    status='failed',
                    details=f"SSH password decryption failed: {str(e)}\nCommand: {command_obj.command}",
                    user=command_obj.user,
                    ip_address=None
                )
                return

            # Établir la connexion SSH
            try:
                logger.info(f"Attempting SSH connection to {firewall.ip_address}")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    firewall.ip_address,
                    username=ssh_user.ssh_username,
                    password=decrypted_password,
                    timeout=10
                )
                logger.info("SSH connection established successfully")

                # Exécuter la commande
                start_time = time.time()
                stdin, stdout, stderr = ssh.exec_command(command_obj.command)
                output = stdout.read().decode()
                error = stderr.read().decode()
                end_time = time.time()
                execution_time = round(end_time - start_time, 2)

                logger.info(f"Command '{command_obj.command}' executed on {firewall.ip_address}")
                logger.info(f"Standard Output:\n{output}")
                logger.error(f"Standard Error:\n{error}")

                # Sauvegarder la sortie standard même en cas d'erreur
                command_obj.output = output

                # Mettre à jour le statut et le message d'erreur
                if error:
                    command_obj.status = 'failed'
                    command_obj.error_message = error
                    logger.error(f"Command execution error: {error}")
                    command_obj.add_to_history(
                        action='execute_error',
                        status='failed',
                        details=f"Command execution failed: {error}\nCommand: {command_obj.command}\nOutput: {output}",
                        user=command_obj.user,
                        ip_address=None
                    )
                else:
                    command_obj.status = 'completed'
                    logger.info("Command executed successfully")
                    command_obj.add_to_history(
                        action='execute_complete',
                        status='completed',
                        details=f"Command executed successfully in {execution_time} seconds\nCommand: {command_obj.command}\nOutput: {output}",
                        user=command_obj.user,
                        ip_address=None
                    )

                # Sauvegarder la commande dans tous les cas
                command_obj.save()
                ssh.close()
                logger.info("SSH connection closed")

            except Exception as e:
                logger.error(f"SSH connection/execution error: {str(e)}")
                command_obj.status = 'failed'
                command_obj.error_message = str(e)
                command_obj.save()
                command_obj.add_to_history(
                    action='execute_error',
                    status='failed',
                    details=f"SSH connection/execution error: {str(e)}\nCommand: {command_obj.command}",
                    user=command_obj.user,
                    ip_address=None
                )

        except Exception as e:
            logger.error(f"General error in _execute_command_async: {str(e)}")
            command_obj.status = 'failed'
            command_obj.error_message = str(e)
            command_obj.save()
            command_obj.add_to_history(
                action='execute_error',
                status='failed',
                details=f"General error: {str(e)}\nCommand: {command_obj.command}",
                user=command_obj.user,
                ip_address=None
            )

    def execute_multiple_commands(self, firewall_id, commands):
        """
        Exécute plusieurs commandes dans une seule session SSH
        """
        try:
            # Récupérer le pare-feu
            firewall = Firewall.objects.get(id=firewall_id)
            if not firewall.ip_address:
                return Response(
                    {'error': f"Le pare-feu {firewall.name} n'a pas d'adresse IP configurée"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Récupérer l'utilisateur SSH
            ssh_user = SSHUser.objects.get(user=self.request.user)
            decrypted_password = ssh_user.get_ssh_password()

            # Établir une seule connexion SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                firewall.ip_address,
                username=ssh_user.ssh_username,
                password=decrypted_password,
                timeout=10
            )

            results = []
            for cmd in commands:
                # Créer l'enregistrement de la commande
                command_obj = FirewallCommand.objects.create(
                    firewall=firewall,
                    user=self.request.user,
                    command=cmd,
                    status='executing'
                )

                try:
                    # Exécuter la commande dans la même session SSH
                    start_time = time.time()
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    output = stdout.read().decode()
                    error = stderr.read().decode()
                    end_time = time.time()
                    execution_time = round(end_time - start_time, 2)

                    # Mettre à jour les paramètres avec toutes les informations importantes
                    command_obj.parameters = {
                        'firewall_info': {
                            'id': str(firewall.id),
                            'name': firewall.name,
                            'ip_address': firewall.ip_address,
                            'model': firewall.model,
                            'version': firewall.version
                        },
                        'command_info': {
                            'raw_command': cmd,
                            'execution_time': execution_time,
                            'timestamp': datetime.now().isoformat(),
                            'user': {
                                'id': str(self.request.user.id),
                                'username': self.request.user.username
                            }
                        },
                        'ssh_info': {
                            'username': ssh_user.ssh_username,
                            'connection_time': execution_time
                        },
                        'output_info': {
                            'has_error': bool(error),
                            'error_message': error if error else None,
                            'output_length': len(output)
                        }
                    }

                    # Mettre à jour le statut et les résultats
                    command_obj.output = output
                    if error:
                        command_obj.status = 'failed'
                        command_obj.error_message = error
                        command_obj.parameters['error_info'] = {
                            'type': 'CommandError',
                            'message': error,
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        command_obj.status = 'completed'
                    command_obj.save()

                    results.append({
                        'command': cmd,
                        'status': command_obj.status,
                        'output': output,
                        'error': error if error else None,
                        'parameters': command_obj.parameters
                    })

                except Exception as e:
                    command_obj.status = 'failed'
                    command_obj.error_message = str(e)
                    command_obj.parameters.update({
                        'error_info': {
                            'type': type(e).__name__,
                            'message': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                    })
                    command_obj.save()
                    results.append({
                        'command': cmd,
                        'status': 'failed',
                        'error': str(e),
                        'parameters': command_obj.parameters
                    })

            # Fermer la connexion SSH
            ssh.close()

            return Response({
                'status': 'success',
                'results': results
            })

        except Firewall.DoesNotExist:
            return Response(
                {'error': 'Pare-feu non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except SSHUser.DoesNotExist:
            return Response(
                {'error': 'Utilisateur SSH non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def execute_multiple(self, request):
        """
        Endpoint pour exécuter plusieurs commandes
        """
        firewall_id = request.data.get('firewall_id')
        commands = request.data.get('commands', [])

        if not firewall_id or not commands:
            return Response(
                {'error': 'firewall_id et commands sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self.execute_multiple_commands(firewall_id, commands)

    def _open_interactive_session(self, host: str, username: str, password: str) -> Tuple[paramiko.SSHClient, any]:
        """Open a single interactive SSH session and return (client, channel)."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password, timeout=10)
        channel = ssh.invoke_shell()
        channel.settimeout(1)
        return ssh, channel

    def _read_until_prompt(self, channel: any, timeout: float = 15.0) -> str:
        """Read channel output until we detect a prompt or timeout."""
        import time
        start = time.time()
        buffer: List[str] = []
        prompt_markers = ['FortiGate #', 'FortiGate-VMX #', '# ', '$ ', '> ', 'C:>']
        while time.time() - start < timeout:
            try:
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                    if chunk:
                        buffer.append(chunk)
                        # pager markers: remove and continue
                        if '--More--' in chunk:
                            try:
                                channel.send(' ')
                            except Exception:
                                pass
                        # detect prompt
                        if any(marker in chunk for marker in prompt_markers):
                            break
                else:
                    time.sleep(0.05)
            except Exception:
                # timeout on read, keep looping until global timeout
                time.sleep(0.05)
        return ''.join(buffer)

    @action(detail=False, methods=['post'], url_path='execute-template')
    def execute_template(self, request):
        """
        Execute a list of commands (template) on a single firewall using ONE interactive SSH session.
        Body: { firewall_id: str, commands: string[] }
        Returns: { status: 'success', results: [{command, status, output, error}] }
        """
        firewall_id = request.data.get('firewall_id')
        commands = request.data.get('commands', [])

        if not firewall_id or not isinstance(commands, list) or len(commands) == 0:
            return Response(
                {'error': 'firewall_id et commands sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            firewall = Firewall.objects.get(id=firewall_id)
        except Firewall.DoesNotExist:
            return Response({'error': 'Pare-feu non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        try:
            ssh_user = SSHUser.objects.get(user=request.user)
            decrypted_password = ssh_user.get_ssh_password()
        except SSHUser.DoesNotExist:
            return Response({'error': 'Utilisateur SSH non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Erreur de déchiffrement SSH: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        results = []
        ssh = None
        channel = None
        try:
            # Open one interactive session
            ssh, channel = self._open_interactive_session(
                firewall.ip_address,
                ssh_user.ssh_username,
                decrypted_password
            )

            # Prime the prompt
            try:
                channel.send('\n')
            except Exception:
                pass
            _ = self._read_until_prompt(channel, timeout=5.0)

            # Execute each command within the same session
            for cmd in commands:
                cmd_str = str(cmd).strip()
                if not cmd_str:
                    continue

                # Track per-command record
                command_obj = FirewallCommand.objects.create(
                    firewall=firewall,
                    user=request.user,
                    command=cmd_str,
                    status='executing'
                )

                try:
                    channel.send(cmd_str + '\n')
                    output = self._read_until_prompt(channel, timeout=30.0)

                    command_obj.output = output
                    command_obj.status = 'completed'
                    command_obj.save()

                    results.append({
                        'command': cmd_str,
                        'status': 'completed',
                        'output': output,
                        'error': None
                    })
                except Exception as e:
                    command_obj.status = 'failed'
                    command_obj.error_message = str(e)
                    command_obj.save()
                    results.append({
                        'command': cmd_str,
                        'status': 'failed',
                        'output': command_obj.output or '',
                        'error': str(e)
                    })

            return Response({'status': 'success', 'results': results})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                if channel:
                    channel.close()
            except Exception:
                pass
            try:
                if ssh:
                    ssh.close()
            except Exception:
                pass

    @action(detail=False, methods=['post'])
    def save_config(self, request):
        try:
            firewall_id = request.data.get('firewall_id')
            command = request.data.get('command')
            
            if not firewall_id or not command:
                return Response({
                    'error': 'Firewall ID and command are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer un ID unique pour la tâche
            task_id = f"config_task_{time.strftime('%Y%m%d_%H%M%S')}"
            
            # Récupérer le firewall
            from command_service.models import Firewall
            firewall = Firewall.objects.get(id=firewall_id)
            
            # Ajouter la tâche à la queue
            config_task_queue.put({
                'task_id': task_id,
                'firewalls': [firewall],
                'command': command,
                'user': request.user
            })
            
            # Initialiser le statut de la tâche
            config_task_status[task_id] = {
                'status': 'pending',
                'progress': 0,
                'message': 'Task queued'
            }
            
            return Response({
                'status': 'success',
                'message': 'Configuration save started',
                'task_id': task_id
            })

        except Exception as e:
            logger.error(f"Error in save_config: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def save_bulk_config(self, request):
        try:
            firewall_ids = request.data.get('firewall_ids', [])
            command = request.data.get('command')
            
            if not firewall_ids or not command:
                return Response({
                    'error': 'Firewall IDs and command are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer un ID unique pour la tâche
            task_id = f"config_task_{time.strftime('%Y%m%d_%H%M%S')}"
            
            # Récupérer les firewalls
            from command_service.models import Firewall
            firewalls = list(Firewall.objects.filter(id__in=firewall_ids))
            
            # Ajouter la tâche à la queue
            config_task_queue.put({
                'task_id': task_id,
                'firewalls': firewalls,
                'command': command,
                'user': request.user
            })
            
            # Initialiser le statut de la tâche
            config_task_status[task_id] = {
                'status': 'pending',
                'progress': 0,
                'message': 'Task queued'
            }
            
            return Response({
                'status': 'success',
                'message': 'Bulk configuration save started',
                'task_id': task_id
            })

        except Exception as e:
            logger.error(f"Error in save_bulk_config: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def check_task_status(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({
                'error': 'No task ID provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if task_id not in config_task_status:
            return Response({
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si la dernière mise à jour date de plus de 2 secondes
        current_time = time.time()
        last_update = config_task_status[task_id].get('last_update', 0)
        
        if current_time - last_update < 2:
            # Si moins de 2 secondes se sont écoulées, renvoyer le statut actuel
            response = Response(config_task_status[task_id])
        else:
            # Sinon, mettre à jour le statut
            config_task_status[task_id]['last_update'] = current_time
            response = Response(config_task_status[task_id])
        
        # Ajouter des en-têtes pour optimiser le cache
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    @action(detail=False, methods=['get'], url_path='download-config/(?P<filename>[^/.]+)')
    def download_config(self, request, filename):
        try:
            filepath = os.path.join(settings.MEDIA_ROOT, 'configs', filename)
            
            if not os.path.exists(filepath):
                return Response(
                    {'error': 'Config file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            with open(filepath, 'rb') as file:
                file_content = file.read()
            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def download_config_file(self, request):
        try:
            filepath = request.query_params.get('filepath')
            if not filepath:
                return Response({
                    'error': 'No file path provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not os.path.exists(filepath):
                return Response({
                    'error': 'Configuration file not found'
                }, status=status.HTTP_404_NOT_FOUND)

            with open(filepath, 'rb') as file:
                file_content = file.read()
            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(filepath)}"'
            return response

        except Exception as e:
            logger.error(f"Error downloading config file: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _execute_ssh_command(self, firewall_id, command):
        # Implement your SSH command execution logic here
        # This is a placeholder - you'll need to implement the actual SSH connection
        # and command execution based on your firewall's requirements
        pass

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        command_obj = self.get_object()
        return Response({
            'id': command_obj.id,
            'status': command_obj.status,
            'output': command_obj.output,
            'error_message': command_obj.error_message,
            'created_at': command_obj.created_at,
            'updated_at': command_obj.updated_at
        })

    @action(detail=False, methods=['get'])
    def get_firewall_commands(self, request):
        firewall_id = request.query_params.get('firewall_id')
        if firewall_id:
            commands = self.get_queryset().filter(firewall_id=firewall_id)
            serializer = self.get_serializer(commands, many=True)
            return Response(serializer.data)
        return Response({
            'error': 'firewall_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        command_obj = self.get_object()
        
        # Vérifier si la commande est déjà en cours d'exécution
        if command_obj.status in ['executing']:
            return Response(
                {'error': 'La commande est déjà en cours d\'exécution'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si la commande a déjà été exécutée avec succès
        if command_obj.status == 'completed':
            return Response(
                {'error': 'La commande a déjà été exécutée avec succès'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Exécuter la commande de manière asynchrone
        self._execute_command_async(command_obj, command_obj.firewall)

        return Response({
            'status': 'executing',
            'message': 'La commande est en cours d\'exécution'
        })

class ExecuteCommandView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FirewallCommandExecuteSerializer(data=request.data)
        if serializer.is_valid():
            try:
                firewall_id = serializer.validated_data['firewall_id']
                command = serializer.validated_data['command']

                logger.info(f"Executing command on firewall {firewall_id}: {command}")

                firewall = Firewall.objects.get(id=firewall_id)
                ssh_user = SSHUser.objects.get(user=request.user)

                # Créer l'enregistrement de la commande
                command_obj = FirewallCommand.objects.create(
                    firewall=firewall,
                    user=request.user,
                    command=command,
                    status='executing'
                )
                
                # Ajouter l'entrée initiale dans l'historique
                command_obj.add_to_history(
                    action='execute_start',
                    status='executing',
                    details=f"Starting command execution on {firewall.name}\nCommand: {command}",
                    user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                try:
                    # Déchiffrer le mot de passe SSH
                    decrypted_password = ssh_user.get_ssh_password()

                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    logger.info(f"Connecting to {firewall.ip_address} with user {ssh_user.ssh_username}")
                    
                    ssh.connect(
                        firewall.ip_address,
                        username=ssh_user.ssh_username,
                        password=decrypted_password,
                        timeout=10
                    )

                    logger.info("Executing command...")
                    stdin, stdout, stderr = ssh.exec_command(command)
                    output = stdout.read().decode()
                    error = stderr.read().decode()

                    logger.info(f"Command '{command}' executed on {firewall.ip_address}")
                    logger.info(f"Standard Output:\n{output}")
                    logger.error(f"Standard Error:\n{error}")

                    # Sauvegarder la sortie standard même en cas d'erreur
                    command_obj.output = output

                    if error:
                        command_obj.status = 'failed'
                        command_obj.error_message = error
                        logger.error(f"Command error: {error}")
                        command_obj.add_to_history(
                            action='execute_error',
                            status='failed',
                            details=f"Command execution failed: {error}\nCommand: {command}",
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        command_obj.status = 'completed'
                        logger.info("Command executed successfully")
                        command_obj.add_to_history(
                            action='execute_complete',
                            status='completed',
                            details=f"Command executed successfully\nCommand: {command}",
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                    # Sauvegarder la commande dans tous les cas
                    command_obj.save()
                    ssh.close()

                    return Response({
                        'status': command_obj.status,
                        'output': output,
                        'error_message': error if error else None
                    })

                except Exception as e:
                    command_obj.status = 'failed'
                    command_obj.error_message = str(e)
                    command_obj.add_to_history(
                        action='execute_error',
                        status='failed',
                        details=f"Unexpected error: {str(e)}\nCommand: {command}",
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    command_obj.save()
                    logger.error(f"Unexpected error: {str(e)}")
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            except Firewall.DoesNotExist:
                logger.error(f"Firewall not found with ID: {firewall_id}")
                return Response(
                    {'error': 'Firewall not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except SSHUser.DoesNotExist:
                logger.error(f"SSH user not found for user: {request.user.username}")
                return Response(
                    {'error': 'SSH user not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
