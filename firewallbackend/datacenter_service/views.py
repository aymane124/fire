from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Prefetch
from .models import DataCenter
from .serializers import DataCenterSerializer
from firewall_service.models import FirewallType, Firewall

class DataCenterViewSet(viewsets.ModelViewSet):
    queryset = DataCenter.objects.all()
    serializer_class = DataCenterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DataCenter.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        instance.add_to_history(
            action='create',
            status='success',
            details=f"DataCenter '{instance.name}' created",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.add_to_history(
            action='update',
            status='success',
            details=f"DataCenter '{instance.name}' updated",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        instance.add_to_history(
            action='delete',
            status='success',
            details=f"DataCenter '{instance.name}' deleted",
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=True, methods=['get'])
    def firewalls(self, request, pk=None):
        datacenter = self.get_object()
        firewalls = datacenter.firewalls.all()
        datacenter.add_to_history(
            action='list_firewalls',
            status='success',
            details=f"Listed {firewalls.count()} firewalls",
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({
            'count': firewalls.count(),
            'firewalls': [{'id': f.id, 'name': f.name} for f in firewalls]
        })

    @action(detail=True, methods=['get'])
    def firewall_types(self, request, pk=None):
        datacenter = self.get_object()
        firewall_types = datacenter.firewall_types.all()
        datacenter.add_to_history(
            action='list_firewall_types',
            status='success',
            details=f"Listed {firewall_types.count()} firewall types",
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({
            'count': firewall_types.count(),
            'firewall_types': [{'id': ft.id, 'name': ft.name} for ft in firewall_types]
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        user = request.user
        total_datacenters = DataCenter.objects.filter(owner=user).count()
        active_datacenters = DataCenter.objects.filter(owner=user, is_active=True).count()
        total_firewalls = DataCenter.objects.filter(owner=user).aggregate(
            total=Count('firewalls')
        )['total']
        total_firewall_types = DataCenter.objects.filter(owner=user).aggregate(
            total=Count('firewall_types')
        )['total']

        return Response({
            'total_datacenters': total_datacenters,
            'active_datacenters': active_datacenters,
            'total_firewalls': total_firewalls,
            'total_firewall_types': total_firewall_types
        })

    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """
        Retourne la hiérarchie complète des datacenters, types de pare-feu et pare-feu
        """
        user = request.user
        
        # Précharger les relations pour optimiser les performances
        datacenters = DataCenter.objects.filter(owner=user).prefetch_related(
            Prefetch(
                'firewall_types',
                queryset=FirewallType.objects.all().prefetch_related(
                    Prefetch(
                        'firewalls',
                        queryset=Firewall.objects.all()
                    )
                )
            )
        )

        hierarchy_data = []
        for dc in datacenters:
            dc_data = {
                'id': str(dc.id),
                'name': dc.name,
                'description': dc.description,
                'firewall_types': []
            }
            
            for ft in dc.firewall_types.all():
                ft_data = {
                    'id': str(ft.id),
                    'name': ft.name,
                    'description': ft.description,
                    'firewalls': [
                        {
                            'id': str(fw.id),
                            'name': fw.name,
                            'ip_address': fw.ip_address
                        }
                        for fw in ft.firewalls.all()
                    ]
                }
                dc_data['firewall_types'].append(ft_data)
            
            hierarchy_data.append(dc_data)

        return Response(hierarchy_data) 