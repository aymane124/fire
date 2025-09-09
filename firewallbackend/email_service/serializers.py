from rest_framework import serializers
from .models import EmailLog, AutomatedEmailSchedule, AutomatedEmailExecution, CommandExecutionResult, CommandTemplate
from django.contrib.auth import get_user_model
from firewall_service.models import Firewall

User = get_user_model()


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class FirewallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Firewall
        fields = ['id', 'name', 'ip_address', 'firewall_type']


class AutomatedEmailScheduleSerializer(serializers.ModelSerializer):
    recipients = UserSerializer(many=True, read_only=True)
    firewalls = FirewallSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    firewall_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = AutomatedEmailSchedule
        fields = [
            'id', 'name', 'description', 'send_time', 'timezone',
            'recipients', 'include_all_users', 'email_subject', 'email_template',
            'firewalls', 'commands_to_execute', 'is_active', 'last_sent', 'next_send',
            'created_by', 'created_at', 'updated_at',
            'recipient_ids', 'firewall_ids'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'last_sent', 'next_send']

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        recipient_ids = validated_data.pop('recipient_ids', [])
        firewall_ids = validated_data.pop('firewall_ids', [])
        
        logger.info(f"📝 [SERIALIZER] Création du planning")
        logger.info(f"   - Firewall IDs reçus: {firewall_ids}")
        logger.info(f"   - Recipient IDs reçus: {recipient_ids}")
        
        # Créer le planning
        schedule = AutomatedEmailSchedule.objects.create(**validated_data)
        
        # Ajouter les destinataires
        if recipient_ids:
            recipients = User.objects.filter(id__in=recipient_ids)
            schedule.recipients.set(recipients)
            logger.info(f"   ✅ [SERIALIZER] {recipients.count()} destinataires ajoutés")
        
        # Ajouter les firewalls
        if firewall_ids:
            firewalls = Firewall.objects.filter(id__in=firewall_ids)
            schedule.firewalls.set(firewalls)
            logger.info(f"   ✅ [SERIALIZER] {firewalls.count()} firewalls ajoutés")
            for fw in firewalls:
                logger.info(f"      - {fw.name} ({fw.ip_address})")
        else:
            logger.warning(f"   ⚠️ [SERIALIZER] Aucun firewall ID fourni!")
        
        # Calculer la prochaine date d'envoi
        schedule.next_send = schedule.calculate_next_send()
        schedule.save()
        
        logger.info(f"   ✅ [SERIALIZER] Planning créé avec ID: {schedule.id}")
        return schedule

    def update(self, instance, validated_data):
        recipient_ids = validated_data.pop('recipient_ids', None)
        firewall_ids = validated_data.pop('firewall_ids', None)
        
        # Mettre à jour les champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Mettre à jour les destinataires si fournis
        if recipient_ids is not None:
            recipients = User.objects.filter(id__in=recipient_ids)
            instance.recipients.set(recipients)
        
        # Mettre à jour les firewalls si fournis
        if firewall_ids is not None:
            firewalls = Firewall.objects.filter(id__in=firewall_ids)
            instance.firewalls.set(firewalls)
        
        # Recalculer la prochaine date d'envoi
        instance.next_send = instance.calculate_next_send()
        instance.save()
        
        return instance


class CommandExecutionResultSerializer(serializers.ModelSerializer):
    firewall = FirewallSerializer(read_only=True)
    
    class Meta:
        model = CommandExecutionResult
        fields = '__all__'


class AutomatedEmailExecutionSerializer(serializers.ModelSerializer):
    schedule = AutomatedEmailScheduleSerializer(read_only=True)
    command_results = CommandExecutionResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = AutomatedEmailExecution
        fields = '__all__'


class EmailScheduleListSerializer(serializers.ModelSerializer):
    recipients_count = serializers.SerializerMethodField()
    firewalls_count = serializers.SerializerMethodField()
    last_execution_status = serializers.SerializerMethodField()
    
    class Meta:
        model = AutomatedEmailSchedule
        fields = [
            'id', 'name', 'description', 'send_time', 'timezone',
            'recipients_count', 'firewalls_count', 'is_active', 
            'last_sent', 'next_send', 'last_execution_status',
            'created_at'
        ]
    
    def get_recipients_count(self, obj):
        return obj.get_recipients().count()
    
    def get_firewalls_count(self, obj):
        return obj.firewalls.count()
    
    def get_last_execution_status(self, obj):
        last_execution = obj.executions.first()
        return last_execution.status if last_execution else None


class CommandTemplateSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    
    class Meta:
        model = CommandTemplate
        fields = ['id', 'command', 'command_type', 'description', 'created_at', 'owner']
        read_only_fields = ['id', 'created_at', 'owner']
