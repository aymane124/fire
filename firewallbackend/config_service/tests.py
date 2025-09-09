from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from auth_service.models import User
from firewall_service.models import Firewall, FirewallType
from .models import FirewallConfig
import json
import uuid

class ConfigServiceTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test firewall type
        self.firewall_type = FirewallType.objects.create(
            name='Test Type',
            description='Test Description',
            attributes_schema={'test': 'schema'},
            data_center_id=uuid.uuid4(),
            owner=self.user
        )
        
        # Create test firewall
        self.firewall = Firewall.objects.create(
            name='Test Firewall',
            ip_address='192.168.1.1',
            data_center_id=uuid.uuid4(),
            firewall_type=self.firewall_type,
            owner=self.user
        )
        
        # Create test configuration
        self.config_data = {
            'rules': [
                {'action': 'allow', 'protocol': 'tcp', 'port': 80},
                {'action': 'deny', 'protocol': 'tcp', 'port': 22}
            ],
            'policies': {
                'default_action': 'deny',
                'logging': True
            }
        }
        
        self.config = FirewallConfig.objects.create(
            firewall=self.firewall,
            config_data=self.config_data,
            owner=self.user
        )
        
        # Setup API client
        self.client = APIClient()
        
        # URLs
        self.config_list_url = reverse('config_service:firewall-config-list')
        self.config_detail_url = reverse('config_service:firewall-config-detail', args=[str(self.config.id)])
        self.latest_config_url = reverse('config_service:firewall-config-get-latest-config')
        
        # Login
        self.client.force_authenticate(user=self.user)

    def test_create_firewall_config(self):
        """Test creating a new firewall configuration"""
        new_config_data = {
            'firewall': str(self.firewall.id),
            'config_data': {
                'rules': [
                    {'action': 'allow', 'protocol': 'tcp', 'port': 443}
                ],
                'policies': {
                    'default_action': 'allow',
                    'logging': False
                }
            }
        }
        
        response = self.client.post(self.config_list_url, new_config_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FirewallConfig.objects.count(), 2)
        
        # Verify the owner was set correctly
        config = FirewallConfig.objects.latest('created_at')
        self.assertEqual(config.owner, self.user)

    def test_get_firewall_configs(self):
        """Test retrieving all firewall configurations"""
        response = self.client.get(self.config_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.config.id))

    def test_get_single_config(self):
        """Test retrieving a single firewall configuration"""
        response = self.client.get(self.config_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.config.id))
        self.assertEqual(response.data['config_data'], self.config_data)

    def test_update_config(self):
        """Test updating a firewall configuration"""
        updated_data = {
            'config_data': {
                'rules': [
                    {'action': 'allow', 'protocol': 'tcp', 'port': 8080}
                ],
                'policies': {
                    'default_action': 'allow',
                    'logging': True
                }
            }
        }
        
        response = self.client.put(self.config_detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify a new configuration was created
        self.assertEqual(FirewallConfig.objects.count(), 2)
        
        # Verify the new configuration has the updated data
        new_config = FirewallConfig.objects.latest('created_at')
        self.assertEqual(new_config.config_data, updated_data['config_data'])

    def test_get_latest_config(self):
        """Test getting the latest configuration for a firewall"""
        # Create a second configuration for the same firewall
        new_config_data = {
            'rules': [
                {'action': 'allow', 'protocol': 'udp', 'port': 53}
            ],
            'policies': {
                'default_action': 'allow',
                'logging': True
            }
        }
        
        FirewallConfig.objects.create(
            firewall=self.firewall,
            config_data=new_config_data,
            owner=self.user
        )
        
        # Get latest config
        response = self.client.get(f"{self.latest_config_url}?firewall_id={self.firewall.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['config_data'], new_config_data)

    def test_invalid_config_data(self):
        """Test creating a configuration with invalid data"""
        invalid_data = {
            'firewall': str(self.firewall.id),
            'config_data': {
                'rules': []  # Missing policies field
            }
        }
        
        response = self.client.post(self.config_list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required field', str(response.data))

    def test_unauthorized_access(self):
        """Test unauthorized access to configurations"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.config_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_user_access(self):
        """Test access to configurations by another user"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.force_authenticate(user=other_user)
        
        response = self.client.get(self.config_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
