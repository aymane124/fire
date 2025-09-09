from rest_framework import serializers
from .models import DataCenter

class DataCenterSerializer(serializers.ModelSerializer):
    owner_username = serializers.SerializerMethodField()
    firewall_count = serializers.SerializerMethodField()
    firewall_type_count = serializers.SerializerMethodField()

    class Meta:
        model = DataCenter
        fields = [
            'id', 'name', 'description', 'location', 'latitude', 'longitude',
            'owner', 'owner_username', 'created_at', 'updated_at', 'is_active',
            'firewall_count', 'firewall_type_count', 'historique_datacenter'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 
                          'firewall_count', 'firewall_type_count', 'historique_datacenter']

    def get_owner_username(self, obj):
        return obj.owner.username

    def get_firewall_count(self, obj):
        return obj.get_firewall_count()

    def get_firewall_type_count(self, obj):
        return obj.get_firewall_type_count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['owner_username'] = instance.owner.username
        return representation

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data) 