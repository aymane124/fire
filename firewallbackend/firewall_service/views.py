from rest_framework import viewsets, permissions, status, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import FirewallType, Firewall
from .serializers import FirewallTypeSerializer, FirewallSerializer
from rest_framework.permissions import IsAuthenticated
import csv
import io
from django.core.exceptions import ValidationError
import time
from django.utils import timezone
import asyncio
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor
from asgiref.sync import sync_to_async
from rest_framework.decorators import api_view
from django.http import HttpResponse

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class FirewallTypeViewSet(viewsets.ModelViewSet):
    queryset = FirewallType.objects.all()
    serializer_class = FirewallTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f'Created firewall type: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f'Updated firewall type: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f'Deleted firewall type: {instance.name}',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=True, methods=['get'])
    def get_firewalls(self, request, pk=None):
        firewall_type = self.get_object()
        firewalls = firewall_type.firewalls.all()
        serializer = FirewallSerializer(firewalls, many=True)
        return Response(serializer.data)

class FirewallViewSet(viewsets.ModelViewSet):
    queryset = Firewall.objects.all()
    serializer_class = FirewallSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f'Created firewall: {instance.name} ({instance.ip_address})',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f'Updated firewall: {instance.name} ({instance.ip_address})',
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f'Deleted firewall: {instance.name} ({instance.ip_address})',
            user=self.request.user,
            ip_address=self.request.META.get('REMote_ADDR')
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def all_firewalls(self, request):
        """
        Récupère tous les firewalls de tous les utilisateurs (admin seulement)
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Accès non autorisé. Seuls les administrateurs peuvent voir tous les firewalls."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        firewalls = Firewall.objects.all().select_related('owner', 'firewall_type')
        serializer = self.get_serializer(firewalls, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_firewalls(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        firewall = self.get_object()
        serializer = self.get_serializer(firewall)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def upload_csv(self, request):
        """
        Upload a CSV file to create multiple firewalls.
        Expected CSV format:
        name,ip_address
        """
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        firewall_type_id = request.data.get('firewall_type')

        if not firewall_type_id:
            return Response({'error': 'Firewall type ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            firewall_type = FirewallType.objects.get(id=firewall_type_id)
        except FirewallType.DoesNotExist:
            return Response({'error': 'Invalid firewall type ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            csv_file = io.TextIOWrapper(file.file, encoding='utf-8')
            reader = csv.DictReader(csv_file)

            created_firewalls = []
            errors = []

            for row in reader:
                try:
                    firewall = Firewall.objects.create(
                        name=row['name'],
                        ip_address=row['ip_address'],
                        firewall_type=firewall_type,
                        data_center=firewall_type.data_center,
                        owner=request.user
                    )
                    firewall.add_to_history(
                        action='create',
                        status='success',
                        details=f'Created firewall from CSV: {firewall.name} ({firewall.ip_address})',
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    created_firewalls.append(str(firewall.id))
                except (KeyError, ValidationError) as e:
                    errors.append(f"Error in row {reader.line_num}: {str(e)}")
                except Exception as e:
                    errors.append(f"Unexpected error in row {reader.line_num}: {str(e)}")

            if errors:
                return Response({
                    'success': len(created_firewalls) > 0,
                    'created_count': len(created_firewalls),
                    'error_count': len(errors),
                    'errors': errors
                }, status=status.HTTP_207_MULTI_STATUS)

            return Response({
                'success': True,
                'created_count': len(created_firewalls),
                'firewalls': created_firewalls
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Error processing CSV file: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def ping(self, request, pk=None):
        """Ping a specific firewall and return its status"""
        firewall = self.get_object()
        try:
            # Simple ping command without any parameters
            command = f'ping {firewall.ip_address}'
            
            print(f"Executing ping command: {command}")
            
            # Execute ping using subprocess
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding='cp1252'  # Use Windows encoding for better compatibility
            )
            
            stdout, stderr = process.communicate(timeout=5)
            return_code = process.returncode
            
            # Log the output
            print(f"Ping output for {firewall.ip_address}:")
            print(f"stdout: {stdout if stdout else 'None'}")
            print(f"stderr: {stderr if stderr else 'None'}")
            print(f"return code: {return_code}")
            
            if return_code == 0:
                # Extract response time from output if possible
                output = stdout.lower() if stdout else ''
                response_time = None
                if 'time=' in output:
                    try:
                        time_str = output.split('time=')[1].split('ms')[0].strip()
                        response_time = float(time_str)
                    except:
                        pass
                
                result = {
                    'status': 'online',
                    'response_time': response_time,
                    'message': 'Firewall is reachable'
                }
            else:
                error_msg = stderr if stderr else stdout if stdout else 'Unknown error'
                result = {
                    'status': 'offline',
                    'response_time': None,
                    'message': f'Firewall is not reachable: {error_msg}'
                }
            
            # Add to history
            firewall.add_to_history(
                action='ping',
                status=result['status'],
                details=f"Ping result: {result['message']} (Response time: {result['response_time']}ms)" if result['response_time'] else f"Ping result: {result['message']}",
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except subprocess.TimeoutExpired:
            process.kill()
            error_message = f'Ping timeout after 5 seconds'
            print(f"Error in ping endpoint: {error_message}")
            
            # Add error to history
            firewall.add_to_history(
                action='ping',
                status='error',
                details=error_message,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'status': 'error',
                'response_time': None,
                'message': error_message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = f"Error pinging firewall: {str(e)}"
            print(f"Error in ping endpoint: {error_message}")
            
            # Add error to history
            firewall.add_to_history(
                action='ping',
                status='error',
                details=error_message,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'status': 'error',
                'response_time': None,
                'message': error_message
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def ping_all(self, request):
        """Ping all firewalls and return their statuses"""
        try:
            # Get all firewalls
            firewalls = list(self.get_queryset())
            if not firewalls:
                return Response({
                    'status': 'success',
                    'message': 'No firewalls found',
                    'results': [],
                    'total': 0,
                    'online': 0,
                    'offline': 0,
                    'errors': 0
                }, status=status.HTTP_200_OK)

            results = []
            for firewall in firewalls:
                try:
                    # Simple ping command without any parameters
                    command = f'ping {firewall.ip_address}'
                    
                    print(f"Executing ping command: {command}")
                    
                    # Execute ping using subprocess
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                        encoding='cp1252'  # Use Windows encoding for better compatibility
                    )
                    
                    stdout, stderr = process.communicate(timeout=5)
                    return_code = process.returncode
                    
                    # Log the output
                    print(f"Ping output for {firewall.ip_address}:")
                    print(f"stdout: {stdout if stdout else 'None'}")
                    print(f"stderr: {stderr if stderr else 'None'}")
                    print(f"return code: {return_code}")
                    
                    if return_code == 0:
                        # Extract response time from output if possible
                        output = stdout.lower() if stdout else ''
                        response_time = None
                        if 'time=' in output:
                            try:
                                time_str = output.split('time=')[1].split('ms')[0].strip()
                                response_time = float(time_str)
                            except:
                                pass
                        
                        result = {
                            'status': 'online',
                            'response_time': response_time,
                            'message': 'Firewall is reachable'
                        }
                    else:
                        error_msg = stderr if stderr else stdout if stdout else 'Unknown error'
                        result = {
                            'status': 'offline',
                            'response_time': None,
                            'message': f'Firewall is not reachable: {error_msg}'
                        }
                    
                    # Add to history
                    firewall.add_to_history(
                        action='ping',
                        status=result['status'],
                        details=f"Ping result: {result['message']} (Response time: {result['response_time']}ms)" if result['response_time'] else f"Ping result: {result['message']}",
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    results.append({
                        'id': str(firewall.id),
                        'name': firewall.name,
                        'ip_address': firewall.ip_address,
                        'status': result['status'],
                        'response_time': result['response_time'],
                        'message': result['message']
                    })
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    error_message = f'Ping timeout after 5 seconds'
                    print(f"Error pinging {firewall.ip_address}: {error_message}")
                    
                    firewall.add_to_history(
                        action='ping',
                        status='error',
                        details=error_message,
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    results.append({
                        'id': str(firewall.id),
                        'name': firewall.name,
                        'ip_address': firewall.ip_address,
                        'status': 'error',
                        'response_time': None,
                        'message': error_message
                    })
                    
                except Exception as e:
                    error_message = f"Error pinging firewall: {str(e)}"
                    print(f"Error pinging {firewall.ip_address}: {error_message}")
                    
                    firewall.add_to_history(
                        action='ping',
                        status='error',
                        details=error_message,
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    results.append({
                        'id': str(firewall.id),
                        'name': firewall.name,
                        'ip_address': firewall.ip_address,
                        'status': 'error',
                        'response_time': None,
                        'message': error_message
                    })

            # Calculate statistics
            total = len(results)
            online = sum(1 for r in results if r['status'] == 'online')
            offline = sum(1 for r in results if r['status'] == 'offline')
            errors = sum(1 for r in results if r['status'] == 'error')

            return Response({
                'status': 'success',
                'message': f'Pinged {total} firewalls',
                'results': results,
                'total': total,
                'online': online,
                'offline': offline,
                'errors': errors
            }, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = f"Error pinging all firewalls: {str(e)}"
            print(f"Error in ping_all endpoint: {error_message}")
            return Response({
                'status': 'error',
                'message': error_message,
                'results': [],
                'total': 0,
                'online': 0,
                'offline': 0,
                'errors': 0
            }, status=status.HTTP_200_OK)