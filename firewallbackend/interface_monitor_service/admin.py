from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import InterfaceAlert, InterfaceStatus, AlertExecution


@admin.register(InterfaceAlert)
class InterfaceAlertAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'firewall', 'alert_type', 'check_interval', 
        'is_active', 'last_check', 'next_check', 'created_by'
    ]
    list_filter = [
        'alert_type', 'is_active', 'firewall__firewall_type__name',
        'firewall__data_center__name', 'created_at'
    ]
    search_fields = ['name', 'description', 'firewall__name']
    readonly_fields = ['last_check', 'next_check', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Configuration de l\'alerte', {
            'fields': ('firewall', 'alert_type', 'check_interval', 'threshold_value', 'command_template')
        }),
        ('Conditions personnalisées', {
            'fields': ('conditions',),
            'classes': ('collapse',)
        }),
        ('Destinataires', {
            'fields': ('recipients', 'include_admin', 'include_superuser')
        }),
        ('Statut', {
            'fields': ('is_active', 'last_check', 'last_status', 'next_check')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'firewall', 'firewall__firewall_type', 'firewall__data_center', 'created_by'
        )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nouvelle alerte
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_alerts', 'deactivate_alerts', 'test_alerts']
    
    def activate_alerts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} alertes ont été activées.')
    activate_alerts.short_description = "Activer les alertes sélectionnées"
    
    def deactivate_alerts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} alertes ont été désactivées.')
    deactivate_alerts.short_description = "Désactiver les alertes sélectionnées"
    
    def test_alerts(self, request, queryset):
        # Cette action sera implémentée pour tester les alertes
        self.message_user(request, f'{queryset.count()} alertes seront testées.')
    test_alerts.short_description = "Tester les alertes sélectionnées"


@admin.register(InterfaceStatus)
class InterfaceStatusAdmin(admin.ModelAdmin):
    list_display = [
        'interface_name', 'alert', 'status', 'bandwidth_in', 
        'bandwidth_out', 'error_count', 'last_seen'
    ]
    list_filter = [
        'status', 'alert__alert_type', 'alert__firewall__name',
        'last_seen'
    ]
    search_fields = ['interface_name', 'alert__name', 'alert__firewall__name']
    readonly_fields = ['last_seen', 'raw_output']
    
    fieldsets = (
        ('Interface', {
            'fields': ('alert', 'interface_name', 'status')
        }),
        ('Métriques', {
            'fields': ('bandwidth_in', 'bandwidth_out', 'error_count', 'packet_loss')
        }),
        ('Connexion', {
            'fields': ('ip_address', 'mac_address')
        }),
        ('Données', {
            'fields': ('raw_output', 'last_seen')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'alert', 'alert__firewall'
        )


@admin.register(AlertExecution)
class AlertExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'alert', 'status', 'started_at', 'completed_at', 
        'duration', 'interfaces_checked', 'alerts_triggered'
    ]
    list_filter = [
        'status', 'alert__alert_type', 'started_at'
    ]
    search_fields = ['alert__name', 'alert__firewall__name']
    readonly_fields = [
        'started_at', 'completed_at', 'duration', 'interfaces_checked',
        'alerts_triggered', 'emails_sent', 'details', 'error_message'
    ]
    
    fieldsets = (
        ('Exécution', {
            'fields': ('alert', 'status', 'started_at', 'completed_at', 'duration')
        }),
        ('Résultats', {
            'fields': ('interfaces_checked', 'alerts_triggered', 'emails_sent')
        }),
        ('Détails', {
            'fields': ('details', 'error_message')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'alert', 'alert__firewall'
        )
    
    def has_add_permission(self, request):
        return False  # Les exécutions sont créées automatiquement
    
    def has_change_permission(self, request, obj=None):
        return False  # Les exécutions ne peuvent pas être modifiées
