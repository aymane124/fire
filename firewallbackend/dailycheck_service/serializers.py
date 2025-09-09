from rest_framework import serializers
from .models import DailyCheck, CheckCommand

class CheckCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckCommand
        fields = ['id', 'command', 'expected_output', 'actual_output', 'status', 'execution_time']

class DailyCheckSerializer(serializers.ModelSerializer):
    commands = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = DailyCheck
        fields = ['id', 'firewall', 'check_date', 'status', 'notes', 'excel_report', 'commands']
        read_only_fields = ['check_date', 'excel_report']

    def validate_commands(self, value):
        if value and not isinstance(value, list):
            raise serializers.ValidationError("Commands must be provided as a list")
        if value and not all(isinstance(cmd, str) for cmd in value):
            raise serializers.ValidationError("All commands must be strings")
        return value 