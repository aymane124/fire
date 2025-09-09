from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import FirewallConfig
from .serializers import FirewallConfigSerializer

# Create your views here.

class FirewallConfigViewSet(viewsets.ModelViewSet):
    queryset = FirewallConfig.objects.all()
    serializer_class = FirewallConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter configurations to show only those owned by the current user.
        """
        return FirewallConfig.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        Save the firewall configuration with the current user as owner.
        """
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def get_latest_config(self, request):
        """
        Get the latest configuration for a specific firewall.
        """
        firewall_id = request.query_params.get('firewall_id')
        if not firewall_id:
            return Response(
                {"error": "firewall_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        latest_config = FirewallConfig.objects.filter(
            firewall_id=firewall_id,
            owner=request.user
        ).first()

        if not latest_config:
            return Response(
                {"error": "No configuration found for this firewall"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(latest_config)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update a firewall configuration.
        Creates a new version instead of modifying the existing one.
        """
        instance = self.get_object()
        
        # Create a new configuration based on the update data
        new_data = request.data.copy()
        new_data['firewall'] = instance.firewall_id
        
        serializer = self.get_serializer(data=new_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data)
