from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.utils import timezone
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Security configurations
SECURITY_CONFIG = {
    'PASSWORD_MIN_LENGTH': 12,  # Minimum requis
    'PASSWORD_REQUIRE_UPPERCASE': True,
    'PASSWORD_REQUIRE_LOWERCASE': True,
    'PASSWORD_REQUIRE_NUMBERS': True,
    'PASSWORD_REQUIRE_SPECIAL_CHARS': True,
    'PASSWORD_MAX_LENGTH': 128,  # Limite maximale
    'PASSWORD_HISTORY_SIZE': 5,  # Empêcher la réutilisation des 5 derniers mots de passe
    'MAX_LOGIN_ATTEMPTS': 3,  # Réduit pour plus de sécurité
    'LOGIN_ATTEMPT_TIMEOUT': 900,  # 15 minutes en secondes
    'TOKEN_REFRESH_INTERVAL': timedelta(hours=12),  # Rotation plus fréquente
    'TOKEN_BLACKLIST_PREFIX': 'blacklist_token_',
    'SESSION_TIMEOUT': 3600,  # 1 heure
}

def validate_password_complexity(password):
    """Validate password complexity requirements"""
    if len(password) < SECURITY_CONFIG['PASSWORD_MIN_LENGTH']:
        return False, f"Password must be at least {SECURITY_CONFIG['PASSWORD_MIN_LENGTH']} characters long"
    
    if len(password) > SECURITY_CONFIG['PASSWORD_MAX_LENGTH']:
        return False, f"Password must be less than {SECURITY_CONFIG['PASSWORD_MAX_LENGTH']} characters"
    
    if SECURITY_CONFIG['PASSWORD_REQUIRE_UPPERCASE'] and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if SECURITY_CONFIG['PASSWORD_REQUIRE_LOWERCASE'] and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if SECURITY_CONFIG['PASSWORD_REQUIRE_NUMBERS'] and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if SECURITY_CONFIG['PASSWORD_REQUIRE_SPECIAL_CHARS'] and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return False, "Password must contain at least one special character"
    
    # Vérifier les patterns communs de mots de passe faibles
    common_patterns = ['password', '123456', 'qwerty', 'admin', 'user']
    if any(pattern in password.lower() for pattern in common_patterns):
        return False, "Password contains common weak patterns"
    
    # Vérifier la répétition de caractères
    if len(set(password)) < len(password) * 0.7:
        return False, "Password contains too many repeated characters"
    
    return True, "Password meets complexity requirements"

def check_login_attempts(username):
    """Check if user has exceeded maximum login attempts"""
    cache_key = f'login_attempts_{username}'
    attempts = cache.get(cache_key, 0)
    
    if attempts >= SECURITY_CONFIG['MAX_LOGIN_ATTEMPTS']:
        logger.warning(f"Too many login attempts for user: {username}")
        return False
    
    return True

def increment_login_attempts(username):
    """Increment login attempts counter"""
    cache_key = f'login_attempts_{username}'
    attempts = cache.get(cache_key, 0) + 1
    cache.set(cache_key, attempts, SECURITY_CONFIG['LOGIN_ATTEMPT_TIMEOUT'])

def reset_login_attempts(username):
    """Reset login attempts counter"""
    cache_key = f'login_attempts_{username}'
    cache.delete(cache_key)

def blacklist_token(token):
    """Add token to blacklist"""
    cache_key = f"{SECURITY_CONFIG['TOKEN_BLACKLIST_PREFIX']}{token}"
    cache.set(cache_key, True, SECURITY_CONFIG['TOKEN_REFRESH_INTERVAL'].total_seconds())

def is_token_blacklisted(token):
    """Check if token is blacklisted"""
    cache_key = f"{SECURITY_CONFIG['TOKEN_BLACKLIST_PREFIX']}{token}"
    return cache.get(cache_key, False)

def rotate_refresh_token(refresh_token):
    """Rotate refresh token"""
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return str(token)
    except Exception as e:
        logger.error(f"Error rotating refresh token: {str(e)}")
        return None 