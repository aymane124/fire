from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import ServiceHistory
from .serializers import ServiceHistorySerializer

class ServiceHistoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceHistory.objects.all()
    serializer_class = ServiceHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service_name', 'action', 'status']
    ordering_fields = ['timestamp', 'service_name']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par l'utilisateur connecté
        queryset = queryset.filter(user=str(self.request.user))
        
        service_name = self.request.query_params.get('service_name', None)
        if service_name:
            queryset = queryset.filter(service_name=service_name)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # Group actions by service
        services = {}
        total_actions = 0
        
        for item in serializer.data:
            service_name = item['service_name']
            if service_name not in services:
                services[service_name] = {
                    'actions': [],
                    'total_actions': 0,
                    'last_updated': item['timestamp']
                }
            
            services[service_name]['actions'].append({
                'id': item['id'],
                'action': item['action'],
                'action_description': item['details'],
                'entity_name': service_name,
                'user': item['user'],
                'timestamp': item['timestamp'],
                'details': item['details']
            })
            services[service_name]['total_actions'] += 1
            total_actions += 1
            
            # Update last_updated if this action is more recent
            if item['timestamp'] > services[service_name]['last_updated']:
                services[service_name]['last_updated'] = item['timestamp']
        
        return Response({
            'services': services,
            'total_actions': total_actions,
            'last_updated': timezone.now().isoformat()
        }) 