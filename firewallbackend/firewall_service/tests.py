from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import uuid
from auth_service.models import User
from .models import FirewallType

class FirewallServiceTests(TestCase):
    def setUp(self):
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Créer un client API authentifié
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Données de test
        self.firewall_type_data = {
            'name': 'Test Firewall Type',
            'description': 'Test Description',
            'attributes_schema': {'key': 'value'},
            'data_center_id': str(uuid.uuid4())
        }
        
        self.firewall_data = {
            'name': 'Test Firewall',
            'ip_address': '192.168.1.1',
            'data_center_id': str(uuid.uuid4())
        }

    def test_create_firewall_type(self):
        """Test la création d'un type de firewall"""
        url = reverse('firewall_service:firewall-type-list')
        response = self.client.post(url, self.firewall_type_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.firewall_type_data['name'])
        self.assertEqual(response.data['owner_username'], self.user.username)
        return response.data['id']

    def test_list_firewall_types(self):
        """Test la liste des types de firewall"""
        # Créer d'abord un type de firewall
        self.test_create_firewall_type()
        
        url = reverse('firewall_service:firewall-type-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_firewall_type(self):
        """Test la récupération d'un type de firewall spécifique"""
        # Créer d'abord un type de firewall
        firewall_type_id = self.test_create_firewall_type()
        
        url = reverse('firewall_service:firewall-type-detail', args=[firewall_type_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.firewall_type_data['name'])

    def test_create_firewall(self):
        """Test la création d'un firewall"""
        # Créer d'abord un type de firewall
        firewall_type_id = self.test_create_firewall_type()
        
        # Ajouter l'ID du type de firewall aux données
        self.firewall_data['firewall_type'] = firewall_type_id
        
        url = reverse('firewall_service:firewall-list')
        response = self.client.post(url, self.firewall_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.firewall_data['name'])
        self.assertEqual(response.data['owner_username'], self.user.username)
        return response.data['id']

    def test_list_firewalls(self):
        """Test la liste des firewalls"""
        # Créer d'abord un firewall
        self.test_create_firewall()
        
        url = reverse('firewall_service:firewall-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_firewall_details(self):
        """Test la récupération des détails d'un firewall"""
        # Créer d'abord un firewall
        firewall_id = self.test_create_firewall()
        
        url = reverse('firewall_service:firewall-details', args=[firewall_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.firewall_data['name'])

    def test_delete_firewall(self):
        """Test la suppression d'un firewall"""
        # Créer d'abord un firewall
        firewall_id = self.test_create_firewall()
        
        url = reverse('firewall_service:firewall-detail', args=[firewall_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Vérifier que le firewall a bien été supprimé
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_my_firewalls(self):
        """Test la récupération des firewalls de l'utilisateur"""
        # Créer d'abord un firewall
        self.test_create_firewall()
        
        url = reverse('firewall_service:firewall-list') + 'my_firewalls/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_my_types(self):
        """Test la récupération des types de firewall de l'utilisateur"""
        # Créer d'abord un type de firewall
        self.test_create_firewall_type()
        
        url = reverse('firewall_service:firewall-type-list') + 'my_types/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1) 