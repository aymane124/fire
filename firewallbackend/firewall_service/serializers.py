from rest_framework import serializers
from .models import Firewall, FirewallType

class FirewallTypeSerializer(serializers.ModelSerializer):
    data_center_info = serializers.SerializerMethodField()
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = FirewallType
        fields = ('id', 'name', 'description', 'attributes_schema', 
                 'data_center', 'data_center_info', 'owner', 'created_at', 'historique_firewall')
        read_only_fields = ('id', 'created_at', 'owner', 'historique_firewall')

    def get_data_center_info(self, obj):
        if obj.data_center:
            return {
                'id': obj.data_center.id,
                'name': obj.data_center.name
            }
        return None

class FirewallSerializer(serializers.ModelSerializer):
    data_center_info = serializers.SerializerMethodField()

    class Meta:
        model = Firewall
        fields = ('id', 'name', 'ip_address', 'data_center', 'data_center_info',
                 'firewall_type', 'owner', 'ssh_user', 'ssh_password', 'ssh_port',
                 'created_at', 'historique_firewall')
        read_only_fields = ('id', 'created_at', 'owner', 'historique_firewall')
        extra_kwargs = {
            'ssh_password': {'write_only': True}  # Ne pas exposer le mot de passe en lecture
        }

    def get_data_center_info(self, obj):
        if obj.data_center:
            return {
                'id': obj.data_center.id,
                'name': obj.data_center.name
            }
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['firewall_type'] = FirewallTypeSerializer(instance.firewall_type).data
        return data 