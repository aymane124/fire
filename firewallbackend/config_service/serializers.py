from rest_framework import serializers
from .models import FirewallConfig

class FirewallConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirewallConfig
        fields = ('id', 'firewall', 'config_data', 'owner', 'created_at', 
                 'updated_at', 'version', 'is_active')
        read_only_fields = ('id', 'created_at', 'updated_at', 'version')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['firewall_name'] = instance.firewall.name
        return data

    def validate_config_data(self, value):
        """
        Validate that the config_data contains valid firewall configuration.
        Add any specific validation rules for your firewall configuration here.
        """
        required_fields = ['rules', 'policies']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        return value

    def create(self, validated_data):
        """
        Create a new firewall configuration.
        Set the owner to the current user.
        """
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

class FirewallConfigVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirewallConfig
        fields = ('id', 'version', 'created_at', 'is_active')
        read_only_fields = ('id', 'version', 'created_at', 'is_active') 