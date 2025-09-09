from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from auth_service.models import User

class DataCenterServiceTests(TestCase):
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
        self.datacenter_data = {
            'name': 'Test DataCenter'
        }

    def test_create_datacenter(self):
        """Test la création d'un datacenter"""
        url = reverse('datacenter_service:datacenter-list')
        response = self.client.post(url, self.datacenter_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.datacenter_data['name'])
        self.assertEqual(response.data['owner_username'], self.user.username)
        return response.data['id']

    def test_list_datacenters(self):
        """Test la liste des datacenters"""
        # Créer d'abord un datacenter
        self.test_create_datacenter()
        
        url = reverse('datacenter_service:datacenter-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_datacenter_details(self):
        """Test la récupération des détails d'un datacenter"""
        # Créer d'abord un datacenter
        datacenter_id = self.test_create_datacenter()
        
        url = reverse('datacenter_service:datacenter-detail', args=[datacenter_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.datacenter_data['name'])

    def test_delete_datacenter(self):
        """Test la suppression d'un datacenter"""
        # Créer d'abord un datacenter
        datacenter_id = self.test_create_datacenter()
        
        url = reverse('datacenter_service:datacenter-detail', args=[datacenter_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Vérifier que le datacenter a bien été supprimé
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) 