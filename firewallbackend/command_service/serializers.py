from rest_framework import serializers
from .models import FirewallCommand

class FirewallCommandSerializer(serializers.ModelSerializer):
    firewall_id = serializers.UUIDField(source='firewall.id')
    parameters = serializers.JSONField(default=dict)

    class Meta:
        model = FirewallCommand
        fields = [
            'id', 'firewall', 'firewall_id', 'user', 'command', 'status',
            'output', 'error_message', 'created_at', 'updated_at',
            'historique_command', 'parameters'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'output', 'error_message',
            'created_at', 'updated_at', 'historique_command'
        ]

    def to_representation(self, instance):
        """
        S'assure que les paramètres sont toujours un dictionnaire
        """
        ret = super().to_representation(instance)
        if not ret['parameters']:
            ret['parameters'] = {
                'firewall_info': {
                    'id': str(instance.firewall.id),
                    'name': instance.firewall.name,
                    'ip_address': instance.firewall.ip_address,
                    'type': instance.firewall.firewall_type.name if instance.firewall.firewall_type else None,
                    'data_center': instance.firewall.data_center.name if instance.firewall.data_center else None
                },
                'command_info': {
                    'raw_command': instance.command,
                    'timestamp': instance.created_at.isoformat(),
                    'user': {
                        'id': str(instance.user.id) if instance.user else None,
                        'username': instance.user.username if instance.user else None
                    }
                },
                'status_info': {
                    'initial_status': instance.status,
                    'created_at': instance.created_at.isoformat()
                }
            }
        return ret

class FirewallCommandExecuteSerializer(serializers.Serializer):
    firewall_id = serializers.UUIDField(required=True)
    command = serializers.CharField(required=True)

    def validate_command(self, value):
        """
        Validate that the command is not empty and doesn't contain dangerous operations.
        """
        if not value.strip():
            raise serializers.ValidationError("Command cannot be empty")
        
        # Add security checks for dangerous commands
        dangerous_commands = ['rm -rf', 'mkfs', 'dd', 'format']
        for cmd in dangerous_commands:
            if cmd in value.lower():
                raise serializers.ValidationError(f"Command contains forbidden operation: {cmd}")
        
        return value

class FirewallCommandHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FirewallCommand
        fields = ['id', 'firewall_id', 'command', 'output', 'status', 'executed_at']
        read_only_fields = fields

class FirewallConfigSaveSerializer(serializers.Serializer):
    firewall_id = serializers.UUIDField(required=True)
    command = serializers.CharField(required=True)

    def validate_command(self, value):
        """
        Validate that the command is not empty and doesn't contain dangerous operations.
        Add any specific command validation rules here.
        """
        if not value.strip():
            raise serializers.ValidationError("Command cannot be empty")
        
        # Add security checks for dangerous commands
        dangerous_commands = ['rm -rf', 'mkfs', 'dd', 'format']
        for cmd in dangerous_commands:
            if cmd in value.lower():
                raise serializers.ValidationError(f"Command contains forbidden operation: {cmd}")
        
        return value

    def create(self, validated_data):
        """
        Create a new command and set the user from the context.
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data) 