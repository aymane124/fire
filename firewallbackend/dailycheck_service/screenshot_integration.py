"""
Intégration de la capture de screenshots dans le service dailycheck
"""

import logging
from typing import Dict, Any, Optional
from auth_service.models import SSHUser

logger = logging.getLogger(__name__)

def capture_firewall_screenshot(firewall, user) -> Optional[str]:
    """
    Capture un screenshot du dashboard du firewall en utilisant delaycheckforti
    
    Args:
        firewall: Instance du modèle Firewall
        user: Utilisateur qui exécute la capture
        
    Returns:
        str: Image encodée en base64 ou None en cas d'erreur
    """
    try:
        logger.info(f"Starting screenshot capture for firewall {firewall.name} ({firewall.ip_address})")
        
        # Importer la fonction de capture depuis le service screenshot
        from screenshot_service.delaycheckforti import execute_autonomous_delaycheckforti
        
        # Récupérer les credentials SSH de l'utilisateur
        try:
            ssh_user = SSHUser.objects.get(user=user)
            username = ssh_user.ssh_username
            password = ssh_user.get_ssh_password()
        except SSHUser.DoesNotExist:
            logger.warning(f"No SSH credentials found for user {user}")
            return None
        except Exception as e:
            logger.error(f"Error getting SSH credentials: {e}")
            return None
        
        # Exécuter la capture avec delaycheckforti (timeout ultra-rapide)
        result = execute_autonomous_delaycheckforti(
            ip_address=firewall.ip_address,
            protocol='https',  # Utiliser HTTPS par défaut
            path='/login',
            username=username,
            password=password,
            timeout=5000,  # Timeout réduit à 5 secondes
            wait_after_popup=500,  # Attente réduite
            viewport_width=1366,
            viewport_height=768,
            ignore_https_errors=True
        )
        
        if result['success'] and result['image_base64']:
            logger.info(f"Screenshot captured successfully for firewall {firewall.name}")
            return result['image_base64']
        else:
            error_msg = result.get('error', 'Unknown error during screenshot capture')
            logger.error(f"Screenshot capture failed for firewall {firewall.name}: {error_msg}")
            return None
            
    except Exception as e:
        logger.error(f"Error capturing screenshot for firewall {firewall.name}: {e}")
        return None

def capture_firewall_screenshot_with_fallback(firewall, user) -> Dict[str, Any]:
    """
    Capture un screenshot avec gestion d'erreur et fallback
    
    Args:
        firewall: Instance du modèle Firewall
        user: Utilisateur qui exécute la capture
        
    Returns:
        Dict avec le résultat de la capture
    """
    result = {
        'success': False,
        'screenshot_base64': None,
        'error': None
    }
    
    try:
        # Essayer HTTPS d'abord
        screenshot_base64 = capture_firewall_screenshot(firewall, user)
        
        if screenshot_base64:
            result['success'] = True
            result['screenshot_base64'] = screenshot_base64
        else:
            # Fallback: essayer HTTP si HTTPS échoue
            logger.info(f"HTTPS failed for {firewall.name}, trying HTTP...")
            try:
                from screenshot_service.delaycheckforti import execute_autonomous_delaycheckforti
                ssh_user = SSHUser.objects.get(user=user)
                
                fallback_result = execute_autonomous_delaycheckforti(
                    ip_address=firewall.ip_address,
                    protocol='http',  # Essayer HTTP
                    path='/login',
                    username=ssh_user.ssh_username,
                    password=ssh_user.get_ssh_password(),
                    timeout=5000,  # Timeout réduit à 5 secondes
                    ignore_https_errors=True
                )
                
                if fallback_result['success'] and fallback_result['image_base64']:
                    result['success'] = True
                    result['screenshot_base64'] = fallback_result['image_base64']
                    logger.info(f"HTTP fallback successful for firewall {firewall.name}")
                else:
                    result['error'] = "Both HTTPS and HTTP screenshot capture failed"
                    
            except Exception as fallback_error:
                result['error'] = f"Fallback failed: {str(fallback_error)}"
                
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Screenshot capture completely failed for firewall {firewall.name}: {e}")
    
    return result
