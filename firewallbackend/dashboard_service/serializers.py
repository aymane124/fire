from rest_framework import serializers
from .models import DashboardStats

class DashboardStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardStats
        fields = '__all__'

class DashboardDataSerializer(serializers.Serializer):
    total_firewalls = serializers.IntegerField()
    active_firewalls = serializers.IntegerField()
    total_datacenters = serializers.IntegerField()
    recent_commands = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    system_health = serializers.CharField()
    last_updated = serializers.DateTimeField()
