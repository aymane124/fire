"""
Utilitaires pour la gestion des fichiers
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Classe utilitaire pour la gestion des fichiers
    """
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """
        S'assure qu'un répertoire existe, le crée si nécessaire
        
        Args:
            directory_path: Chemin du répertoire
            
        Returns:
            bool: True si le répertoire existe ou a été créé
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            return False
    
    @staticmethod
    def get_safe_filename(filename: str, max_length: int = 255) -> str:
        """
        Nettoie un nom de fichier pour qu'il soit sûr
        
        Args:
            filename: Nom de fichier original
            max_length: Longueur maximale
            
        Returns:
            str: Nom de fichier nettoyé
        """
        # Caractères interdits
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, '_')
        
        # Limiter la longueur
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename
    
    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Vérifie si un fichier existe
        
        Args:
            filepath: Chemin vers le fichier
            
        Returns:
            bool: True si le fichier existe
        """
        return os.path.exists(filepath) and os.path.isfile(filepath)
    
    @staticmethod
    def get_file_size(filepath: str) -> Optional[int]:
        """
        Récupère la taille d'un fichier
        
        Args:
            filepath: Chemin vers le fichier
            
        Returns:
            int: Taille du fichier en octets, None si erreur
        """
        try:
            return os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Error getting file size for {filepath}: {e}")
            return None
