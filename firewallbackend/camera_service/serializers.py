from rest_framework import serializers
from .models import Camera

class CameraSerializer(serializers.ModelSerializer):
    location_decimal = serializers.SerializerMethodField()
    location_dms = serializers.SerializerMethodField()

    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'ip_address', 'location', 'latitude', 'longitude',
            'owner', 'created_at', 'updated_at', 'is_online', 'last_ping',
            'historique_camera', 'location_decimal', 'location_dms'
        ]
        read_only_fields = [
            'id', 'owner', 'created_at', 'updated_at', 'is_online',
            'last_ping', 'historique_camera', 'location_decimal', 'location_dms'
        ]

    def get_location_decimal(self, obj):
        return obj.get_location_decimal()

    def get_location_dms(self, obj):
        return obj.get_location_dms() 