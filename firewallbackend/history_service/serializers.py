from rest_framework import serializers
from .models import ServiceHistory

class ServiceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceHistory
        fields = '__all__'
        read_only_fields = ('timestamp',) 