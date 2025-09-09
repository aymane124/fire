from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import InterfaceAlert, InterfaceStatus, AlertExecution
from firewall_service.models import Firewall

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les utilisateurs"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class FirewallSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les firewalls"""
    
    class Meta:
        model = Firewall
        fields = ['id', 'name', 'ip_address', 'firewall_type']


class InterfaceStatusSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les statuts d'interfaces"""
    
    class Meta:
        model = InterfaceStatus
        fields = [
            'id', 'alert', 'interface_name', 'status', 'bandwidth_in', 
            'bandwidth_out', 'error_count', 'packet_loss', 'ip_address', 
            'mac_address', 'raw_output', 'last_seen'
        ]
        read_only_fields = ['id', 'last_seen']


class AlertExecutionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les exécutions d'alertes"""
    
    class Meta:
        model = AlertExecution
        fields = [
            'id', 'alert', 'status', 'started_at', 'completed_at', 
            'duration', 'interfaces_checked', 'alerts_triggered', 
            'emails_sent', 'details', 'error_message'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at', 'duration']


class InterfaceAlertSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les alertes d'interfaces"""
    
    # Champs calculés et relations
    recipients = UserSerializer(many=True, read_only=True)
    firewall = FirewallSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    last_check = serializers.DateTimeField(read_only=True)
    next_check = serializers.DateTimeField(read_only=True)
    
    # Statistiques calculées
    total_executions = serializers.SerializerMethodField()
    successful_executions = serializers.SerializerMethodField()
    failed_executions = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = InterfaceAlert
        fields = [
            'id', 'name', 'description', 'firewall', 'alert_type', 
            'check_interval', 'threshold_value', 'command_template', 
            'conditions', 'recipients', 'include_admin', 'include_superuser',
            'is_active', 'last_check', 'last_status', 'next_check',
            'created_by', 'created_at', 'updated_at',
            'total_executions', 'successful_executions', 'failed_executions', 'success_rate'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_total_executions(self, obj):
        """Retourne le nombre total d'exécutions"""
        return obj.executions.count()
    
    def get_successful_executions(self, obj):
        """Retourne le nombre d'exécutions réussies"""
        return obj.executions.filter(status='completed').count()
    
    def get_failed_executions(self, obj):
        """Retourne le nombre d'exécutions échouées"""
        return obj.executions.filter(status='failed').count()
    
    def get_success_rate(self, obj):
        """Calcule le taux de succès"""
        total = self.get_total_executions(obj)
        successful = self.get_successful_executions(obj)
        
        if total > 0:
            return round((successful / total) * 100, 2)
        return 0.0
    
    def validate_check_interval(self, value):
        """Valide l'intervalle de vérification"""
        if value < 60:  # Minimum 1 minute
            raise serializers.ValidationError("L'intervalle de vérification doit être d'au moins 60 secondes")
        
        if value > 86400:  # Maximum 24 heures
            raise serializers.ValidationError("L'intervalle de vérification ne peut pas dépasser 24 heures")
        
        return value
    
    def validate_threshold_value(self, value):
        """Valide la valeur seuil"""
        if value is not None and value < 0:
            raise serializers.ValidationError("La valeur seuil ne peut pas être négative")
        
        return value
    
    def validate_conditions(self, value):
        """Valide les conditions personnalisées"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Les conditions doivent être un objet JSON")
        
        # Vérifier la structure des conditions si elles sont définies
        if value:
            required_fields = ['field', 'operator', 'value']
            valid_operators = ['equals', 'not_equals', 'greater_than', 'less_than', 'contains']
            
            for condition in value.get('conditions', []):
                if not isinstance(condition, dict):
                    raise serializers.ValidationError("Chaque condition doit être un objet")
                
                for field in required_fields:
                    if field not in condition:
                        raise serializers.ValidationError(f"Le champ '{field}' est requis pour chaque condition")
                
                if condition.get('operator') not in valid_operators:
                    raise serializers.ValidationError(f"Opérateur invalide. Utilisez: {', '.join(valid_operators)}")
        
        return value


class AlertCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la création d'alertes"""
    
    class Meta:
        model = InterfaceAlert
        fields = [
            'name', 'description', 'firewall', 'alert_type', 
            'check_interval', 'threshold_value', 'command_template', 
            'conditions', 'recipients', 'include_admin', 'include_superuser',
            'is_active'
        ]
    
    def validate(self, attrs):
        """Validation globale de l'alerte"""
        # Vérifier que le firewall est de type FortiGate si nécessaire
        firewall = attrs.get('firewall')
        if firewall and hasattr(firewall, 'firewall_type'):
            firewall_type = firewall.firewall_type.name.lower()
            if 'forti' not in firewall_type and attrs.get('command_template') == 'show system interface':
                raise serializers.ValidationError(
                    "La commande 'show system interface' est spécifique aux firewalls FortiGate"
                )
        
        # Vérifier que les destinataires sont définis
        recipients = attrs.get('recipients', [])
        include_admin = attrs.get('include_admin', True)
        include_superuser = attrs.get('include_superuser', True)
        
        if not recipients and not include_admin and not include_superuser:
            raise serializers.ValidationError(
                "Au moins un destinataire doit être défini"
            )
        
        return attrs


class AlertUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la mise à jour d'alertes"""
    
    class Meta:
        model = InterfaceAlert
        fields = [
            'name', 'description', 'alert_type', 'check_interval', 
            'threshold_value', 'command_template', 'conditions', 
            'recipients', 'include_admin', 'include_superuser', 'is_active'
        ]
    
    def validate(self, attrs):
        """Validation globale de la mise à jour"""
        # Même validation que pour la création
        return super().validate(attrs)


class AlertSummarySerializer(serializers.Serializer):
    """Sérialiseur pour le résumé des alertes"""
    
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    inactive_alerts = serializers.IntegerField()
    overdue_alerts = serializers.IntegerField()
    
    # Statistiques des exécutions
    recent_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    running_executions = serializers.IntegerField()
    success_rate = serializers.FloatField()
    
    # Recommandations
    recommendations = serializers.ListField(child=serializers.CharField())


class InterfaceStatusSummarySerializer(serializers.Serializer):
    """Sérialiseur pour le résumé des statuts d'interfaces"""
    
    total_interfaces = serializers.IntegerField()
    up_interfaces = serializers.IntegerField()
    down_interfaces = serializers.IntegerField()
    error_interfaces = serializers.IntegerField()
    total_bandwidth_in = serializers.FloatField()
    total_bandwidth_out = serializers.FloatField()
    total_errors = serializers.IntegerField()
    health_percentage = serializers.FloatField()


class ExecutionSummarySerializer(serializers.Serializer):
    """Sérialiseur pour le résumé des exécutions"""
    
    total_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    running_executions = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_duration = serializers.FloatField(allow_null=True)


class MonitoringHealthSerializer(serializers.Serializer):
    """Sérialiseur pour la santé du système de surveillance"""
    
    status = serializers.CharField()  # healthy, warning, critical, error
    timestamp = serializers.DateTimeField()
    
    # Détails des alertes
    alerts = AlertSummarySerializer()
    
    # Détails des exécutions
    executions = ExecutionSummarySerializer()
    
    # Recommandations
    recommendations = serializers.ListField(child=serializers.CharField())
    
    # Erreur si applicable
    error = serializers.CharField(allow_null=True)


class TaskResultSerializer(serializers.Serializer):
    """Sérialiseur pour les résultats de tâches"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    task_id = serializers.CharField(allow_null=True)
    
    # Résultats spécifiques
    interfaces_checked = serializers.IntegerField(allow_null=True)
    alerts_triggered = serializers.IntegerField(allow_null=True)
    emails_sent = serializers.IntegerField(allow_null=True)
    
    # Erreur si applicable
    error = serializers.CharField(allow_null=True)
    
    # Détails supplémentaires
    details = serializers.DictField(allow_null=True)


class AlertTestSerializer(serializers.Serializer):
    """Sérialiseur pour les tests d'alertes"""
    
    alert_id = serializers.UUIDField()
    test_type = serializers.ChoiceField(choices=['manual', 'scheduled', 'immediate'])
    parameters = serializers.DictField(required=False)


class AlertScheduleSerializer(serializers.Serializer):
    """Sérialiseur pour la planification d'alertes"""
    
    alert_id = serializers.UUIDField()
    schedule_time = serializers.DateTimeField()
    repeat_interval = serializers.IntegerField(required=False)  # en secondes
    enabled = serializers.BooleanField(default=True)


class BulkAlertActionSerializer(serializers.Serializer):
    """Sérialiseur pour les actions en lot sur les alertes"""
    
    alert_ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=['activate', 'deactivate', 'delete', 'test'])
    parameters = serializers.DictField(required=False)


class AlertFilterSerializer(serializers.Serializer):
    """Sérialiseur pour le filtrage des alertes"""
    
    firewall_id = serializers.UUIDField(required=False)
    alert_type = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False)
    created_by = serializers.UUIDField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    search = serializers.CharField(required=False)
    
    # Pagination
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    
    # Tri
    ordering = serializers.CharField(required=False, default='-created_at')
    
    def validate_ordering(self, value):
        """Valide le champ de tri"""
        valid_fields = [
            'name', '-name', 'created_at', '-created_at', 'updated_at', '-updated_at',
            'firewall__name', '-firewall__name', 'alert_type', '-alert_type',
            'is_active', '-is_active', 'last_check', '-last_check'
        ]
        
        if value not in valid_fields:
            raise serializers.ValidationError(f"Champ de tri invalide. Utilisez: {', '.join(valid_fields)}")
        
        return value


class AlertExportSerializer(serializers.Serializer):
    """Sérialiseur pour l'export des alertes"""
    
    format = serializers.ChoiceField(choices=['json', 'csv', 'xlsx'])
    filters = AlertFilterSerializer(required=False)
    include_details = serializers.BooleanField(default=False)
    include_executions = serializers.BooleanField(default=False)
    include_status = serializers.BooleanField(default=False)
