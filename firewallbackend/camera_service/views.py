from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Camera, PingResult
from .serializers import CameraSerializer
from rest_framework.permissions import IsAuthenticated
import csv
from io import StringIO
from .utils import parse_coordinates, format_location
from django.db import models
import re
import pythonping
from django.utils import timezone
import threading
from queue import Queue
import time
import logging
import uuid
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queue pour stocker les tâches de ping
ping_task_queue = Queue()
# Dictionnaire pour stocker l'état des tâches
ping_task_status = {}

def ping_background_worker():
    while True:
        try:
            task = ping_task_queue.get()
            if task is None:
                break
                
            task_id = task['task_id']
            ping_task_status[task_id] = {
                'status': 'running',
                'progress': 0,
                'message': 'Starting ping process...',
                'last_update': time.time()
            }
            
            try:
                cameras = task['cameras']
                user = task['user']
                
                total_cameras = len(cameras)
                processed_cameras = 0
                results = []
                
                for camera in cameras:
                    try:
                        # Mettre à jour le statut toutes les 2 secondes seulement
                        current_time = time.time()
                        if current_time - ping_task_status[task_id]['last_update'] >= 2:
                            ping_task_status[task_id].update({
                                'message': f'Pinging {camera.name}...',
                                'last_update': current_time
                            })
                        
                        # Effectuer le ping avec un timeout de 2 secondes
                        response = pythonping.ping(camera.ip_address, count=1, timeout=2)
                        
                        # Vérifier si le ping a réussi
                        is_online = response.success()
                        
                        # Mettre à jour le statut de la caméra
                        camera.is_online = is_online
                        camera.last_ping = timezone.now()
                        camera.save()

                        # Créer un enregistrement de résultat de ping
                        ping_result = PingResult.objects.create(
                            id=str(uuid.uuid4()),
                            camera=camera,
                            status='online' if is_online else 'offline',
                            response_time=response.rtt_avg_ms if is_online else None,
                            task_id=task_id
                        )

                        # Ajouter l'historique
                        camera.add_to_history(
                            action='ping_all',
                            status='success' if is_online else 'offline',
                            details=f"Ping to {camera.ip_address} {'succeeded' if is_online else 'failed'}",
                            user=user,
                            ip_address=None
                        )
                        
                        results.append({
                            'id': camera.id,
                            'name': camera.name,
                            'ip_address': camera.ip_address,
                            'status': 'online' if is_online else 'offline',
                            'response_time': response.rtt_avg_ms if is_online else None,
                            'timestamp': camera.last_ping
                        })
                        
                    except Exception as e:
                        logger.error(f"Error pinging camera {camera.id}: {str(e)}")
                        # En cas d'erreur, marquer la caméra comme hors ligne
                        camera.is_online = False
                        camera.last_ping = timezone.now()
                        camera.save()

                        # Créer un enregistrement de résultat de ping pour l'erreur
                        ping_result = PingResult.objects.create(
                            id=str(uuid.uuid4()),
                            camera=camera,
                            status='error',
                            error_message=str(e),
                            task_id=task_id
                        )

                        # Ajouter l'historique de l'erreur
                        camera.add_to_history(
                            action='ping_all',
                            status='error',
                            details=f"Ping to {camera.ip_address} failed: {str(e)}",
                            user=user,
                            ip_address=None
                        )
                        
                        results.append({
                            'id': camera.id,
                            'name': camera.name,
                            'ip_address': camera.ip_address,
                            'status': 'error',
                            'error': str(e),
                            'timestamp': camera.last_ping
                        })
                    
                    processed_cameras += 1
                    # Mettre à jour la progression toutes les 2 secondes seulement
                    current_time = time.time()
                    if current_time - ping_task_status[task_id]['last_update'] >= 2:
                        ping_task_status[task_id].update({
                            'progress': int((processed_cameras / total_cameras) * 100),
                            'last_update': current_time
                        })
                
                # Mettre à jour last_ping_all pour toutes les caméras
                for camera in cameras:
                    camera.last_ping_all = timezone.now()
                    camera.save()
                
                ping_task_status[task_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': 'All cameras pinged',
                    'results': results,
                    'last_update': time.time()
                })
                
            except Exception as e:
                logger.error(f"Error in background task: {str(e)}")
                ping_task_status[task_id].update({
                    'status': 'failed',
                    'message': str(e),
                    'last_update': time.time()
                })
            
            finally:
                ping_task_queue.task_done()
                
        except Exception as e:
            logger.error(f"Error in worker thread: {str(e)}")
            continue

# Démarrer le worker thread
ping_worker_thread = threading.Thread(target=ping_background_worker, daemon=True)
ping_worker_thread.start()

class CameraViewSet(viewsets.ModelViewSet):
    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Camera.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f"Camera '{instance.name}' created",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f"Camera '{instance.name}' updated",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f"Camera '{instance.name}' deleted",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def ping(self, request, pk=None):
        camera = self.get_object()
        try:
            # Effectuer le ping avec un timeout de 2 secondes
            response = pythonping.ping(camera.ip_address, count=1, timeout=2)
            
            # Vérifier si le ping a réussi
            is_online = response.success()
            
            # Mettre à jour le statut de la caméra
            camera.is_online = is_online
            camera.last_ping = timezone.now()
            camera.save()

            # Ajouter l'historique
            camera.add_to_history(
                action='ping',
                status='success' if is_online else 'offline',
                details=f"Ping to {camera.ip_address} {'succeeded' if is_online else 'failed'}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'status': 'online' if is_online else 'offline',
                'ip_address': camera.ip_address,
                'response_time': response.rtt_avg_ms if is_online else None,
                'timestamp': camera.last_ping
            })
            
        except Exception as e:
            # En cas d'erreur, marquer la caméra comme hors ligne
            camera.is_online = False
            camera.last_ping = timezone.now()
            camera.save()

            # Ajouter l'historique de l'erreur
            camera.add_to_history(
                action='ping',
                status='error',
                details=f"Ping to {camera.ip_address} failed: {str(e)}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'status': 'error',
                'ip_address': camera.ip_address,
                'error': str(e),
                'timestamp': camera.last_ping
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def ping_all(self, request):
        try:
            # Vérifier si un ping_all a été effectué dans les 2 dernières minutes
            last_ping_all = Camera.objects.filter(
                owner=request.user,
                last_ping_all__isnull=False
            ).order_by('-last_ping_all').first()

            if last_ping_all and last_ping_all.last_ping_all:
                time_since_last_ping = timezone.now() - last_ping_all.last_ping_all
                if time_since_last_ping < timedelta(minutes=2):
                    remaining_seconds = int((timedelta(minutes=2) - time_since_last_ping).total_seconds())
                    return Response({
                        'status': 'error',
                        'message': f'Veuillez attendre {remaining_seconds} secondes avant de relancer un ping_all'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Créer un ID unique pour la tâche
            task_id = f"ping_task_{time.strftime('%Y%m%d_%H%M%S')}"
            
            # Récupérer les caméras
            cameras = self.get_queryset()
            
            # Ajouter la tâche à la queue
            ping_task_queue.put({
                'task_id': task_id,
                'cameras': list(cameras),
                'user': request.user
            })
            
            # Initialiser le statut de la tâche
            ping_task_status[task_id] = {
                'status': 'pending',
                'progress': 0,
                'message': 'Task queued',
                'last_update': time.time()
            }
            
            return Response({
                'status': 'success',
                'message': 'Ping process started',
                'task_id': task_id
            })

        except Exception as e:
            logger.error(f"Error in ping_all: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def check_ping_status(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({
                'error': 'No task ID provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if task_id not in ping_task_status:
            return Response({
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si la dernière mise à jour date de plus de 2 secondes
        current_time = time.time()
        last_update = ping_task_status[task_id].get('last_update', 0)
        
        if current_time - last_update < 2:
            # Si moins de 2 secondes se sont écoulées, renvoyer le statut actuel
            response = Response(ping_task_status[task_id])
        else:
            # Sinon, mettre à jour le statut
            ping_task_status[task_id]['last_update'] = current_time
            response = Response(ping_task_status[task_id])
        
        # Ajouter des en-têtes pour optimiser le cache
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    @action(detail=False, methods=['post'])
    def upload_csv(self, request):
        print("\n=== Starting CSV Upload ===")
        print(f"Request Files: {request.FILES}")
        print(f"Request Content Type: {request.content_type}")
        
        if 'file' not in request.FILES:
            print("Error: No file in request.FILES")
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        print(f"File name: {file.name}")
        print(f"File size: {file.size} bytes")
        
        if not file.name.endswith('.csv'):
            print(f"Error: Invalid file extension: {file.name}")
            return Response(
                {'error': 'File must be a CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Essayer différents encodages
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    file.seek(0)  # Réinitialiser la position du fichier
                    content = file.read().decode(encoding)
                    print(f"Successfully decoded file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                print("Error: Could not decode file with any supported encoding")
                return Response(
                    {'error': 'Impossible de décoder le fichier. Veuillez utiliser un encodage UTF-8, Latin-1 ou ISO-8859-1.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Créer un StringIO avec newline='' pour gérer correctement les caractères de nouvelle ligne
            csv_file = StringIO(content, newline='')
            reader = csv.DictReader(csv_file, quoting=csv.QUOTE_MINIMAL)
            
            # Vérifier les en-têtes du CSV
            print(f"CSV Headers: {reader.fieldnames}")
            
            # Mapper les noms de champs insensibles à la casse
            field_mapping = {
                'name': ['name', 'Name', 'NAME'],
                'ip_address': ['ip_address', 'IP Address', 'IP_ADDRESS', 'ipaddress'],
                'latitude': ['latitude', 'Latitude', 'LATITUDE'],
                'longitude': ['longitude', 'Longitude', 'LONGITUDE'],
                'location': ['location', 'Location', 'LOCATION', 'coordinates', 'Coordinates', 'COORDINATES']
            }
            
            # Créer un mapping inverse pour les en-têtes du CSV
            header_mapping = {}
            for standard_field, possible_names in field_mapping.items():
                for name in possible_names:
                    if name in reader.fieldnames:
                        header_mapping[name] = standard_field
                        break
            
            print(f"Header mapping: {header_mapping}")
            
            required_fields = ['name', 'ip_address']
            created_count = 0
            updated_count = 0
            errors = []

            def parse_dms(dms_str):
                try:
                    # Nettoyer les caractères spéciaux
                    clean_dms = dms_str.replace('Â°', '°').replace('\\s+', '').strip()
                    
                    # Extraire les degrés, minutes, secondes et direction
                    match = re.match(r'(\d+)°(\d+)\'([\d.]+)"([NSEW])', clean_dms)
                    if not match:
                        return None
                    
                    degrees, minutes, seconds, direction = match.groups()
                    decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
                    
                    # Ajuster le signe selon la direction
                    if direction in ['S', 'W']:
                        decimal = -decimal
                    
                    return decimal
                except Exception:
                    return None

            def parse_coordinates(location_str):
                if not location_str:
                    return None, None
                
                try:
                    # Nettoyer les caractères spéciaux
                    clean_location = location_str.replace('Â°', '°').replace('\\s+', ' ').strip()
                    
                    # Vérifier si c'est au format DMS
                    if '°' in clean_location:
                        parts = clean_location.split()
                        if len(parts) != 2:
                            return None, None
                        
                        lat_dms, lng_dms = parts
                        lat = parse_dms(lat_dms)
                        lng = parse_dms(lng_dms)
                        
                        if lat is not None and lng is not None:
                            return lat, lng
                    
                    # Format décimal standard
                    coords = [float(coord.strip()) for coord in clean_location.split(',')]
                    if len(coords) == 2:
                        return coords[0], coords[1]
                    
                    return None, None
                except Exception:
                    return None, None

            for row_num, row in enumerate(reader, start=2):  # start=2 car la première ligne est l'en-tête
                try:
                    print(f"\nProcessing row {row_num}: {row}")
                    
                    # Nettoyer les valeurs des champs et appliquer le mapping
                    cleaned_row = {}
                    for header, value in row.items():
                        if header in header_mapping:
                            cleaned_row[header_mapping[header]] = value.strip() if isinstance(value, str) else value
                    
                    print(f"Cleaned row: {cleaned_row}")
                    
                    # Vérifier les champs requis
                    missing_fields = [field for field in required_fields if field not in cleaned_row]
                    if missing_fields:
                        errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                        continue

                    # Vérifier si la caméra existe déjà
                    camera = Camera.objects.filter(
                        name=cleaned_row['name'],
                        owner=request.user
                    ).first()

                    if camera:
                        # Mise à jour de la caméra existante
                        for field, value in cleaned_row.items():
                            setattr(camera, field, value)
                        camera.save()
                        updated_count += 1

                        # Ajouter l'historique
                        camera.add_to_history(
                            action='update_csv',
                            status='success',
                            details=f"Camera updated from CSV import",
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        # Création d'une nouvelle caméra
                        camera = Camera.objects.create(
                            **cleaned_row,
                            owner=request.user
                        )
                        created_count += 1

                        # Ajouter l'historique
                        camera.add_to_history(
                            action='create_csv',
                            status='success',
                            details=f"Camera created from CSV import",
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            return Response({
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def get_ping_history(self, request):
        try:
            camera_id = request.query_params.get('camera_id')
            if not camera_id:
                return Response({
                    'error': 'No camera ID provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Récupérer les 100 derniers résultats de ping pour la caméra
            ping_results = PingResult.objects.filter(
                camera_id=camera_id
            ).order_by('-timestamp')[:100]

            results = [{
                'id': result.id,
                'status': result.status,
                'response_time': result.response_time,
                'error_message': result.error_message,
                'timestamp': result.timestamp
            } for result in ping_results]

            return Response({
                'camera_id': camera_id,
                'total_results': len(results),
                'results': results
            })

        except Exception as e:
            logger.error(f"Error getting ping history: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 