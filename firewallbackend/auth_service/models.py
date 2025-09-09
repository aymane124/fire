import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from auth_service.utils.crypto import (
    encrypt_user_data, decrypt_user_data,
    encrypt_ssh_data, decrypt_ssh_data
)
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    # Suppression du champ raw_password pour éviter le stockage en clair

    # Override the groups and user_permissions fields to add custom related_name
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='auth_service_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='auth_service_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        # Hache le mot de passe pour Django (pas de stockage en clair)
        super().set_password(raw_password)
        # Sauvegarde l'utilisateur
        self.save()

    def has_ssh_credentials(self):
        """Vérifie si l'utilisateur a des identifiants SSH configurés"""
        try:
            ssh_user = self.ssh_credentials
            return bool(ssh_user.ssh_username and ssh_user.ssh_password)
        except SSHUser.DoesNotExist:
            return False

    def get_ssh_credentials(self):
        """Récupère les identifiants SSH de l'utilisateur"""
        try:
            return self.ssh_credentials
        except SSHUser.DoesNotExist:
            return None

class SSHUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ssh_credentials')
    ssh_username = models.CharField(max_length=100)
    ssh_password = models.TextField()  # Stockage du mot de passe chiffré SSH en texte
    ssh_private_key = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SSH User"
        verbose_name_plural = "SSH Users"

    def __str__(self):
        return f"SSH User for {self.user.username}"

    def set_ssh_password(self, raw_password):
        """Chiffre et stocke le mot de passe SSH"""
        try:
            # Vérifier que le mot de passe est une chaîne
            if not isinstance(raw_password, str):
                raise ValueError("Password must be a string")

            # Chiffrer le mot de passe
            encrypted_password = encrypt_ssh_data(raw_password)
            
            # Stocker directement la chaîne chiffrée
            self.ssh_password = encrypted_password
            self.save(update_fields=['ssh_password', 'updated_at'])
            
        except Exception as e:
            logger.error(f"Error in set_ssh_password: {str(e)}")
            raise ValueError(f"Failed to encrypt SSH password: {str(e)}")

    def get_ssh_password(self):
        """Déchiffre et retourne le mot de passe SSH"""
        try:
            if not self.ssh_password:
                return None

            # Récupérer le mot de passe chiffré
            if isinstance(self.ssh_password, bytes):
                encrypted_password = self.ssh_password.decode('utf-8')
            else:
                encrypted_password = str(self.ssh_password)

            # Vérifier le préfixe
            if not encrypted_password.startswith('ENC:'):
                return encrypted_password

            # Déchiffrer le mot de passe
            return decrypt_ssh_data(encrypted_password)

        except Exception as e:
            logger.error(f"Error in get_ssh_password: {str(e)}")
            raise ValueError(f"Failed to decrypt SSH password: {str(e)}")

    def check_ssh_password(self, raw_password):
        """Vérifie si le mot de passe fourni correspond au mot de passe SSH"""
        try:
            stored_password = self.get_ssh_password()
            return stored_password == raw_password
        except Exception as e:
            logger.error(f"Error in check_ssh_password: {str(e)}")
            return False
