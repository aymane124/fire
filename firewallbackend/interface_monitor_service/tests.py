import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import InterfaceAlert, InterfaceStatus, AlertExecution
from firewall_service.models import Firewall, FirewallType
from datacenter_service.models import DataCenter

User = get_user_model()


class InterfaceMonitorServiceTestCase(TestCase):
    """Tests de base pour le service de surveillance des interfaces"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Créer un datacenter de test
        self.datacenter = DataCenter.objects.create(
            name='Test DC',
            location='Test Location',
            description='Test Description'
        )
        
        # Créer un type de firewall de test
        self.firewall_type = FirewallType.objects.create(
            name='FortiGate',
            description='FortiGate Firewall',
            attributes_schema={},
            data_center=self.datacenter,
            owner=self.user
        )
        
        # Créer un firewall de test
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center=self.datacenter,
            firewall_type=self.firewall_type,
            owner=self.user
        )
    
    def test_create_interface_alert(self):
        """Test de création d'une alerte d'interface"""
        alert = InterfaceAlert.objects.create(
            name='Test Alert',
            description='Test Description',
            firewall=self.firewall,
            alert_type='interface_down',
            check_interval=300,
            created_by=self.user
        )
        
        self.assertEqual(alert.name, 'Test Alert')
        self.assertEqual(alert.alert_type, 'interface_down')
        self.assertEqual(alert.check_interval, 300)
        self.assertTrue(alert.is_active)
        self.assertEqual(alert.created_by, self.user)
    
    def test_alert_recipients(self):
        """Test de la gestion des destinataires d'alerte"""
        # Créer des utilisateurs supplémentaires
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            created_by=self.user
        )
        
        # Ajouter des destinataires
        alert.recipients.add(user2)
        alert.include_admin = True
        alert.save()
        
        # Vérifier les destinataires
        recipients = alert.get_recipients()
        self.assertIn(user2, recipients)
        self.assertIn(self.user, recipients)  # Créateur de l'alerte
    
    def test_alert_next_check_calculation(self):
        """Test du calcul de la prochaine vérification"""
        alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            check_interval=300,
            created_by=self.user
        )
        
        # Calculer la prochaine vérification
        next_check = alert.calculate_next_check()
        
        # Vérifier que la prochaine vérification est dans le futur
        self.assertGreater(next_check, timezone.now())
        
        # Vérifier que l'intervalle est respecté
        expected_time = timezone.now() + timezone.timedelta(seconds=300)
        self.assertAlmostEqual(
            next_check.timestamp(),
            expected_time.timestamp(),
            delta=10  # Tolérance de 10 secondes
        )
    
    def test_alert_should_check_now(self):
        """Test de la logique de vérification des alertes"""
        alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            check_interval=300,
            created_by=self.user
        )
        
        # L'alerte doit être vérifiée immédiatement si pas de next_check
        self.assertTrue(alert.should_check_now())
        
        # Programmer une vérification future
        alert.next_check = timezone.now() + timezone.timedelta(hours=1)
        alert.save()
        
        # L'alerte ne doit pas être vérifiée maintenant
        self.assertFalse(alert.should_check_now())
        
        # Programmer une vérification passée
        alert.next_check = timezone.now() - timezone.timedelta(minutes=1)
        alert.save()
        
        # L'alerte doit être vérifiée maintenant
        self.assertTrue(alert.should_check_now())


class InterfaceStatusTestCase(TestCase):
    """Tests pour les modèles de statut d'interface"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.datacenter = DataCenter.objects.create(
            name='Test DC',
            location='Test Location'
        )
        
        self.firewall_type = FirewallType.objects.create(
            name='FortiGate',
            description='FortiGate Firewall',
            attributes_schema={},
            data_center=self.datacenter,
            owner=self.user
        )
        
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center=self.datacenter,
            firewall_type=self.firewall_type,
            owner=self.user
        )
        
        self.alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            created_by=self.user
        )
    
    def test_create_interface_status(self):
        """Test de création d'un statut d'interface"""
        status_obj = InterfaceStatus.objects.create(
            alert=self.alert,
            interface_name='port1',
            status='up',
            bandwidth_in=100.0,
            bandwidth_out=50.0,
            error_count=0,
            ip_address='192.168.1.10'
        )
        
        self.assertEqual(status_obj.interface_name, 'port1')
        self.assertEqual(status_obj.status, 'up')
        self.assertEqual(status_obj.bandwidth_in, 100.0)
        self.assertEqual(status_obj.bandwidth_out, 50.0)
        self.assertEqual(status_obj.error_count, 0)
        self.assertEqual(status_obj.ip_address, '192.168.1.10')
    
    def test_interface_status_str_representation(self):
        """Test de la représentation en chaîne du statut d'interface"""
        status_obj = InterfaceStatus.objects.create(
            alert=self.alert,
            interface_name='port1',
            status='down'
        )
        
        expected_str = f"port1 - down ({self.alert.name})"
        self.assertEqual(str(status_obj), expected_str)


class AlertExecutionTestCase(TestCase):
    """Tests pour les modèles d'exécution d'alerte"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.datacenter = DataCenter.objects.create(
            name='Test DC',
            location='Test Location'
        )
        
        self.firewall_type = FirewallType.objects.create(
            name='FortiGate',
            description='FortiGate Firewall',
            attributes_schema={},
            data_center=self.datacenter,
            owner=self.user
        )
        
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center=self.datacenter,
            firewall_type=self.firewall_type,
            owner=self.user
        )
        
        self.alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            created_by=self.user
        )
    
    def test_create_alert_execution(self):
        """Test de création d'une exécution d'alerte"""
        execution = AlertExecution.objects.create(
            alert=self.alert,
            status='running'
        )
        
        self.assertEqual(execution.alert, self.alert)
        self.assertEqual(execution.status, 'running')
        self.assertIsNotNone(execution.started_at)
        self.assertIsNone(execution.completed_at)
    
    def test_execution_mark_completed(self):
        """Test du marquage d'une exécution comme terminée"""
        execution = AlertExecution.objects.create(
            alert=self.alert,
            status='running'
        )
        
        details = {'interfaces_checked': 5, 'alerts_triggered': 1}
        execution.mark_completed(details)
        
        self.assertEqual(execution.status, 'completed')
        self.assertIsNotNone(execution.completed_at)
        self.assertIsNotNone(execution.duration)
        self.assertEqual(execution.details, details)
    
    def test_execution_mark_failed(self):
        """Test du marquage d'une exécution comme échouée"""
        execution = AlertExecution.objects.create(
            alert=self.alert,
            status='running'
        )
        
        error_message = "Connection timeout"
        details = {'error_type': 'connection_error'}
        execution.mark_failed(error_message, details)
        
        self.assertEqual(execution.status, 'failed')
        self.assertIsNotNone(execution.completed_at)
        self.assertIsNotNone(execution.duration)
        self.assertEqual(execution.error_message, error_message)
        self.assertEqual(execution.details, details)


class APITestCase(APITestCase):
    """Tests pour l'API REST"""
    
    def setUp(self):
        """Configuration initiale pour les tests API"""
        self.client = APIClient()
        
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Créer un superuser
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Créer les données de test
        self.datacenter = DataCenter.objects.create(
            name='Test DC',
            location='Test Location'
        )
        
        self.firewall_type = FirewallType.objects.create(
            name='FortiGate',
            description='FortiGate Firewall',
            attributes_schema={},
            data_center=self.datacenter,
            owner=self.user
        )
        
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center=self.datacenter,
            firewall_type=self.firewall_type,
            owner=self.user
        )
        
        self.alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            created_by=self.user
        )
    
    def test_list_alerts_authenticated(self):
        """Test de la liste des alertes pour un utilisateur authentifié"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('interface_monitor_service:interface-alert-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Alert')
    
    def test_list_alerts_unauthenticated(self):
        """Test de la liste des alertes pour un utilisateur non authentifié"""
        url = reverse('interface_monitor_service:interface-alert-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_alert_authenticated(self):
        """Test de création d'alerte pour un utilisateur authentifié"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('interface_monitor_service:interface-alert-list')
        data = {
            'name': 'New Alert',
            'description': 'New Description',
            'firewall': self.firewall.id,
            'alert_type': 'interface_up',
            'check_interval': 600
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InterfaceAlert.objects.count(), 2)
        
        new_alert = InterfaceAlert.objects.get(name='New Alert')
        self.assertEqual(new_alert.created_by, self.user)
    
    def test_test_alert_action(self):
        """Test de l'action de test d'alerte"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('interface_monitor_service:interface-alert-test', args=[self.alert.id])
        
        with patch('interface_monitor_service.views.test_alert') as mock_test:
            mock_test.delay.return_value = MagicMock(id='test-task-id')
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'scheduled')
            self.assertEqual(response.data['task_id'], 'test-task-id')
    
    def test_activate_alert_action(self):
        """Test de l'action d'activation d'alerte"""
        self.client.force_authenticate(user=self.user)
        
        # Désactiver l'alerte d'abord
        self.alert.is_active = False
        self.alert.save()
        
        url = reverse('interface_monitor_service:interface-alert-activate', args=[self.alert.id])
        
        with patch('interface_monitor_service.views.schedule_next_check') as mock_schedule:
            mock_schedule.delay.return_value = True
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['message'], 'Alerte activée')
            
            # Vérifier que l'alerte est active
            self.alert.refresh_from_db()
            self.assertTrue(self.alert.is_active)


class ParserTestCase(TestCase):
    """Tests pour le parser FortiGate"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        from .parsers import FortiGateInterfaceParser
        self.parser = FortiGateInterfaceParser()
    
    def test_parse_fortigate_output(self):
        """Test du parsing de la sortie FortiGate"""
        sample_output = """
port1 is up
    IP: 192.168.1.1/24
    MAC: 00:11:22:33:44:55
    MTU: 1500
    Speed: 1000Mbps
    Duplex: Full

port2 is down
    IP: 192.168.2.1/24
    MAC: 00:11:22:33:44:56
    MTU: 1500
    Speed: 1000Mbps
    Duplex: Full

port3 is up
    IP: 10.0.0.1/24
    MAC: 00:11:22:33:44:57
    MTU: 1500
    Speed: 1000Mbps
    Duplex: Full
"""
        
        interfaces = self.parser.parse(sample_output)
        
        self.assertEqual(len(interfaces), 3)
        
        # Vérifier port1
        port1 = next(i for i in interfaces if i['name'] == 'port1')
        self.assertEqual(port1['status'], 'up')
        self.assertEqual(port1['ip_address'], '192.168.1.1')
        self.assertEqual(port1['mac_address'], '00:11:22:33:44:55')
        
        # Vérifier port2
        port2 = next(i for i in interfaces if i['name'] == 'port2')
        self.assertEqual(port2['status'], 'down')
        self.assertEqual(port2['ip_address'], '192.168.2.1')
        
        # Vérifier port3
        port3 = next(i for i in interfaces if i['name'] == 'port3')
        self.assertEqual(port3['status'], 'up')
        self.assertEqual(port3['ip_address'], '10.0.0.1')
    
    def test_parse_empty_output(self):
        """Test du parsing d'une sortie vide"""
        interfaces = self.parser.parse("")
        self.assertEqual(len(interfaces), 0)
    
    def test_parse_malformed_output(self):
        """Test du parsing d'une sortie malformée"""
        malformed_output = "Invalid output format\nNo interface information"
        interfaces = self.parser.parse(malformed_output)
        self.assertEqual(len(interfaces), 0)
    
    def test_get_interface_summary(self):
        """Test du calcul du résumé des interfaces"""
        interfaces = [
            {'name': 'port1', 'status': 'up', 'bandwidth_in': 100, 'bandwidth_out': 50, 'error_count': 0},
            {'name': 'port2', 'status': 'down', 'bandwidth_in': 0, 'bandwidth_out': 0, 'error_count': 5},
            {'name': 'port3', 'status': 'up', 'bandwidth_in': 200, 'bandwidth_out': 100, 'error_count': 1}
        ]
        
        summary = self.parser.get_interface_summary(interfaces)
        
        self.assertEqual(summary['total_interfaces'], 3)
        self.assertEqual(summary['up_interfaces'], 2)
        self.assertEqual(summary['down_interfaces'], 1)
        self.assertEqual(summary['error_interfaces'], 0)
        self.assertEqual(summary['total_bandwidth_in'], 300)
        self.assertEqual(summary['total_bandwidth_out'], 150)
        self.assertEqual(summary['total_errors'], 6)
        self.assertEqual(summary['health_percentage'], 66.67)


class ServiceTestCase(TestCase):
    """Tests pour les services de surveillance"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.datacenter = DataCenter.objects.create(
            name='Test DC',
            location='Test Location'
        )
        
        self.firewall_type = FirewallType.objects.create(
            name='FortiGate',
            description='FortiGate Firewall',
            attributes_schema={},
            data_center=self.datacenter,
            owner=self.user
        )
        
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center=self.datacenter,
            firewall_type=self.firewall_type,
            owner=self.user
        )
        
        self.alert = InterfaceAlert.objects.create(
            name='Test Alert',
            firewall=self.firewall,
            alert_type='interface_down',
            created_by=self.user
        )
    
    @patch('interface_monitor_service.services.InterfaceMonitorService._connect_to_firewall')
    @patch('interface_monitor_service.services.InterfaceMonitorService._execute_interface_command')
    def test_check_interfaces_success(self, mock_execute, mock_connect):
        """Test de la vérification réussie des interfaces"""
        from .services import InterfaceMonitorService
        
        # Mock de la sortie de commande
        mock_execute.return_value = """
port1 is up
    IP: 192.168.1.1/24
port2 is down
    IP: 192.168.2.1/24
"""
        
        service = InterfaceMonitorService(self.alert)
        
        # Exécuter la vérification
        result = service.check_interfaces()
        
        # Vérifier le résultat
        self.assertTrue(result['success'])
        self.assertEqual(result['interfaces_checked'], 2)
        self.assertEqual(result['alerts_triggered'], 1)  # port2 est down
    
    def test_check_alert_conditions(self):
        """Test de la vérification des conditions d'alerte"""
        from .services import InterfaceMonitorService
        
        service = InterfaceMonitorService(self.alert)
        
        # Interfaces de test
        interfaces = [
            {'name': 'port1', 'status': 'up', 'bandwidth_in': 100, 'bandwidth_out': 50, 'error_count': 0},
            {'name': 'port2', 'status': 'down', 'bandwidth_in': 0, 'bandwidth_out': 0, 'error_count': 5}
        ]
        
        # Vérifier les conditions pour une alerte de type 'interface_down'
        alerts_triggered = service._check_alert_conditions(interfaces)
        
        self.assertEqual(len(alerts_triggered), 1)
        self.assertEqual(alerts_triggered[0]['interface']['name'], 'port2')
        self.assertEqual(alerts_triggered[0]['reason'], 'Interface down')


if __name__ == '__main__':
    # Exécuter les tests
    import django
    django.setup()
    
    # Créer et exécuter la suite de tests
    import unittest
    unittest.main()
