"""
Utilitaires de validation pour le service dailycheck
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ValidationUtils:
    """
    Classe utilitaire pour les validations
    """
    
    @staticmethod
    def validate_commands(commands: List[str]) -> Dict[str, Any]:
        """
        Valide une liste de commandes
        
        Args:
            commands: Liste des commandes
            
        Returns:
            Dict: Résultat de la validation
        """
        if not commands:
            return {
                'valid': False,
                'error': 'No commands provided'
            }
        
        if not isinstance(commands, list):
            return {
                'valid': False,
                'error': 'Commands must be provided as a list'
            }
        
        if not all(isinstance(cmd, str) for cmd in commands):
            return {
                'valid': False,
                'error': 'All commands must be strings'
            }
        
        if not all(cmd.strip() for cmd in commands):
            return {
                'valid': False,
                'error': 'Commands cannot be empty'
            }
        
        return {
            'valid': True,
            'error': None
        }
    
    @staticmethod
    def validate_firewalls(firewalls: List) -> Dict[str, Any]:
        """
        Valide une liste de firewalls
        
        Args:
            firewalls: Liste des firewalls
            
        Returns:
            Dict: Résultat de la validation
        """
        if not firewalls:
            return {
                'valid': False,
                'error': 'No firewalls provided'
            }
        
        if not isinstance(firewalls, list):
            return {
                'valid': False,
                'error': 'Firewalls must be provided as a list'
            }
        
        # Vérifier que tous les firewalls ont une IP
        for firewall in firewalls:
            if not hasattr(firewall, 'ip_address') or not firewall.ip_address:
                return {
                    'valid': False,
                    'error': f'Firewall {firewall.name if hasattr(firewall, "name") else "unknown"} has no IP address'
                }
        
        return {
            'valid': True,
            'error': None
        }
    
    @staticmethod
    def validate_daily_check_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les données d'un daily check
        
        Args:
            data: Données à valider
            
        Returns:
            Dict: Résultat de la validation
        """
        required_fields = ['firewall', 'commands']
        
        for field in required_fields:
            if field not in data:
                return {
                    'valid': False,
                    'error': f'Missing required field: {field}'
                }
        
        # Valider les commandes
        commands_validation = ValidationUtils.validate_commands(data['commands'])
        if not commands_validation['valid']:
            return commands_validation
        
        return {
            'valid': True,
            'error': None
        }
