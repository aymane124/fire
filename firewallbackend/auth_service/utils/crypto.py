from cryptography.fernet import Fernet
from django.conf import settings
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import logging

logger = logging.getLogger(__name__)

def get_aes_key():
    if not hasattr(settings, 'ENCRYPTION_KEY'):
        settings.ENCRYPTION_KEY = Fernet.generate_key()
    return settings.ENCRYPTION_KEY

def get_user_encryption_key():
    if not hasattr(settings, 'USER_ENCRYPTION_KEY'):
        settings.USER_ENCRYPTION_KEY = os.urandom(32)  # 256 bits pour AES-256
    return settings.USER_ENCRYPTION_KEY

def get_ssh_encryption_key():
    """Génère ou récupère la clé de chiffrement SSH"""
    if not hasattr(settings, 'SSH_ENCRYPTION_KEY'):
        # Générer une clé de 32 bytes (256 bits) pour ChaCha20
        key = os.urandom(32)
        settings.SSH_ENCRYPTION_KEY = base64.b64encode(key).decode('utf-8')
    return base64.b64decode(settings.SSH_ENCRYPTION_KEY)

def encrypt_text(plain_text):
    key = get_aes_key()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(plain_text.encode('utf-8')) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode('utf-8')  # return as base64 string

def decrypt_text(encrypted_text):
    key = get_aes_key()
    data = base64.b64decode(encrypted_text)  # decode from base64 to bytes
    iv = data[:16]
    ct = data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    pt = decryptor.update(ct) + decryptor.finalize()
    return pt.decode('utf-8')

def encrypt_user_data(plain_text):
    """
    Chiffrement des données utilisateur avec AES-256-GCM
    """
    key = get_user_encryption_key()
    iv = os.urandom(12)  # GCM recommande 12 octets pour l'IV
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Chiffrement
    ct = encryptor.update(plain_text.encode('utf-8')) + encryptor.finalize()
    
    # Combiner IV, tag d'authentification et texte chiffré
    combined = iv + encryptor.tag + ct
    return base64.b64encode(combined).decode('utf-8')

def decrypt_user_data(encrypted_text):
    """
    Déchiffrement des données utilisateur
    """
    key = get_user_encryption_key()
    data = base64.b64decode(encrypted_text)
    
    # Extraire les composants
    iv = data[:12]
    tag = data[12:28]
    ct = data[28:]
    
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    
    pt = decryptor.update(ct) + decryptor.finalize()
    return pt.decode('utf-8')

def encrypt_ssh_data(plain_text):
    """Chiffre les données SSH avec ChaCha20-Poly1305"""
    try:
        # Vérifier que le texte est une chaîne
        if not isinstance(plain_text, str):
            raise ValueError("Input must be a string")

        # Récupérer la clé de chiffrement
        key = get_ssh_encryption_key()
        
        # Créer un objet de chiffrement
        cipher = ChaCha20Poly1305(key)
        
        # Générer un nonce aléatoire
        nonce = os.urandom(12)
        
        # Chiffrer les données
        ciphertext = cipher.encrypt(nonce, plain_text.encode('utf-8'), None)
        
        # Combiner le nonce et le texte chiffré
        encrypted_data = nonce + ciphertext
        
        # Encoder en base64 avec padding correct
        encoded_data = base64.b64encode(encrypted_data).decode('utf-8')
        
        # Ajouter le préfixe
        return 'ENC:' + encoded_data
        
    except Exception as e:
        logger.error(f"Error in encrypt_ssh_data: {str(e)}")
        raise ValueError(f"Failed to encrypt SSH data: {str(e)}")

def decrypt_ssh_data(encrypted_text):
    """Déchiffre les données SSH"""
    try:
        # Vérifier le préfixe
        if not encrypted_text.startswith('ENC:'):
            return encrypted_text

        # Extraire les données chiffrées
        encrypted_data = encrypted_text[4:]
        
        # Nettoyer les données base64
        encrypted_data = encrypted_data.strip()
        
        # Vérifier et corriger le padding base64
        padding = len(encrypted_data) % 4
        if padding:
            encrypted_data += '=' * (4 - padding)
        
        # Décoder les données base64
        try:
            encrypted_data = base64.b64decode(encrypted_data, validate=True)
        except Exception as e:
            logger.error(f"Error decoding base64 data: {str(e)}")
            raise ValueError("Invalid base64 data format")

        # Vérifier la longueur minimale des données
        if len(encrypted_data) < 12:  # 12 bytes pour le nonce
            logger.error("Encrypted data too short")
            raise ValueError("Invalid encrypted data length")

        # Extraire le nonce et les données chiffrées
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Récupérer la clé de chiffrement
        key = get_ssh_encryption_key()
        
        # Déchiffrer avec ChaCha20-Poly1305
        cipher = ChaCha20Poly1305(key)
        try:
            decrypted_data = cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise ValueError("Decryption failed")

        # Convertir en chaîne de caractères
        try:
            return decrypted_data.decode('utf-8', errors='replace')
        except UnicodeDecodeError as e:
            logger.error(f"Error decoding decrypted data to UTF-8: {str(e)}")
            # En cas d'échec du décodage UTF-8, essayer de nettoyer les données
            try:
                cleaned_data = decrypted_data.decode('latin-1').encode('utf-8', errors='replace').decode('utf-8')
                return cleaned_data
            except Exception as e:
                logger.error(f"Error cleaning decrypted data: {str(e)}")
                raise ValueError("Invalid decrypted data format")

    except Exception as e:
        logger.error(f"Error in decrypt_ssh_data: {str(e)}")
        raise ValueError(f"Failed to decrypt SSH data: {str(e)}")

def get_ssh_password(self):
    """Déchiffre le mot de passe SSH"""
    try:
        if not self.ssh_password:
            return None

        # Convertir en str si nécessaire
        if isinstance(self.ssh_password, bytes):
            encrypted_password = self.ssh_password.decode('utf-8')
        else:
            encrypted_password = str(self.ssh_password)

        # Déchiffrer le mot de passe
        return decrypt_ssh_data(encrypted_password)

    except Exception as e:
        logger.error(f"Error in get_ssh_password: {str(e)}")
        raise ValueError(f"Failed to decrypt SSH password: {str(e)}")
