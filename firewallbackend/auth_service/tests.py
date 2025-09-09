from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, SSHUser
import uuid
from .utils import encryption_manager
from auth_service.utils.crypto import encrypt_text, decrypt_text

class AuthServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth_service:auth-register')
        self.login_url = reverse('auth_service:auth-login')
        self.verify_token_url = reverse('auth_service:auth-verify-token')
        self.ssh_user_url = reverse('auth_service:ssh-users-list')
        
        # Données de test
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'password_confirm': 'testpassword123'
        }
        
        self.ssh_user_data = {
            'ssh_username': 'test_ssh',
            'public_key': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ...'
        }

    def test_user_registration(self):
        """Test de l'enregistrement d'un nouvel utilisateur"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('user' in response.data)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)
        
        # Vérifier que l'utilisateur a été créé
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_user_login(self):
        """Test de la connexion d'un utilisateur"""
        # Créer un utilisateur d'abord
        self.client.post(self.register_url, self.user_data)
        
        # Tester la connexion
        login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)

    def test_invalid_login(self):
        """Test de connexion avec des identifiants invalides"""
        login_data = {
            'username': 'wronguser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_verification(self):
        """Test de vérification du token"""
        # Créer un utilisateur et obtenir un token
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        login_response = self.client.post(self.login_url, login_data)
        token = login_response.data['refresh']
        
        # Vérifier le token
        response = self.client.post(self.verify_token_url, {'token': token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_ssh_user_creation(self):
        """Test de création d'un utilisateur SSH"""
        # Créer un utilisateur et obtenir un token
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        login_response = self.client.post(self.login_url, login_data)
        token = login_response.data['access']
        
        # Créer un utilisateur SSH
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.ssh_user_url, self.ssh_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SSHUser.objects.filter(ssh_username='test_ssh').exists())

    def test_ssh_user_list(self):
        """Test de la liste des utilisateurs SSH"""
        # Créer un utilisateur et obtenir un token
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        login_response = self.client.post(self.login_url, login_data)
        token = login_response.data['access']
        
        # Créer un utilisateur SSH
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.post(self.ssh_user_url, self.ssh_user_data)
        
        # Récupérer la liste des utilisateurs SSH
        response = self.client.get(self.ssh_user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier la structure de la réponse paginée
        self.assertTrue('count' in response.data)
        self.assertTrue('results' in response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ssh_username'], 'test_ssh')

class EncryptionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '+1234567890',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        self.ssh_user_data = {
            'ssh_username': 'test_ssh',
            'ssh_password': 'test_ssh_pass'
        }

    def test_user_encryption(self):
        # Créer un utilisateur
        response = self.client.post(
            reverse('auth_service:auth-register'),
            self.user_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Récupérer l'utilisateur de la base de données
        user = User.objects.get(username='testuser')
        
        # Vérifier que les données sensibles sont chiffrées
        self.assertNotEqual(user._encrypted_email, 'test@example.com')
        self.assertNotEqual(user._encrypted_phone_number, '+1234567890')
        
        # Vérifier que le déchiffrement fonctionne
        self.assertEqual(user.decrypted_email, 'test@example.com')
        self.assertEqual(user.decrypted_phone_number, '+1234567890')

    def test_ssh_user_encryption(self):
        # Créer un utilisateur pour le test
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Créer un utilisateur SSH
        ssh_user = SSHUser.objects.create(
            user=user,
            ssh_username='test_ssh',
            ssh_password='test_ssh_pass'
        )
        
        # Vérifier que les données sont chiffrées dans la base
        self.assertNotEqual(ssh_user.ssh_username, 'test_ssh')
        self.assertNotEqual(ssh_user.ssh_password, 'test_ssh_pass')
        
        # Vérifier que le déchiffrement fonctionne
        self.assertEqual(ssh_user.get_ssh_username(), 'test_ssh')
        self.assertEqual(ssh_user.get_ssh_password(), 'test_ssh_pass')

    def test_ssh_user_api(self):
        # Créer un utilisateur et obtenir un token
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        response = self.client.post(
            reverse('auth_service:auth-login'),
            {'username': 'testuser', 'password': 'testpass123'},
            format='json'
        )
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Créer un utilisateur SSH via l'API
        response = self.client.post(
            reverse('auth_service:ssh-users-list'),
            self.ssh_user_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Vérifier que les données sont correctement déchiffrées dans la réponse
        self.assertEqual(response.data['ssh_username'], 'test_ssh')
        self.assertEqual(response.data['ssh_password'], 'test_ssh_pass')
        
        # Récupérer la liste des utilisateurs SSH
        response = self.client.get(reverse('auth_service:ssh-users-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ssh_username'], 'test_ssh')
        self.assertEqual(response.data['results'][0]['ssh_password'], 'test_ssh_pass')

class SSHUserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.ssh_user = SSHUser.objects.create(
            user=self.user,
            ssh_username='testssh',
            ssh_password='testsshpass'
        )

    def test_ssh_password_encryption(self):
        # Test encryption
        self.ssh_user.set_ssh_password('newpass123')
        self.assertNotEqual(self.ssh_user.ssh_password, 'newpass123')  # Should be encrypted
        
        # Test decryption
        self.assertTrue(self.ssh_user.check_ssh_password('newpass123'))
        self.assertFalse(self.ssh_user.check_ssh_password('wrongpass'))
