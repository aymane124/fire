from django.apps import AppConfig
from datetime import timedelta
from .cors import *  # Import all CORS settings


class AuthServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_service'
    verbose_name = 'Authentication Service'

    def ready(self):
        import auth_service.signals  # Import signals when app is ready
        
        # Import security settings
        from .security import SECURITY_CONFIG
        from django.conf import settings
        
        # Add security settings to Django settings
        if not hasattr(settings, 'SECURITY_CONFIG'):
            settings.SECURITY_CONFIG = SECURITY_CONFIG
        
        # Configure JWT settings
        settings.SIMPLE_JWT = {
            'ACCESS_TOKEN_LIFETIME': SECURITY_CONFIG['TOKEN_REFRESH_INTERVAL'],
            'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
            'ROTATE_REFRESH_TOKENS': True,
            'BLACKLIST_AFTER_ROTATION': True,
            'ALGORITHM': 'HS256',
            'SIGNING_KEY': settings.SECRET_KEY,
            'VERIFYING_KEY': None,
            'AUTH_HEADER_TYPES': ('Bearer',),
            'USER_ID_FIELD': 'id',
            'USER_ID_CLAIM': 'user_id',
            'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
            'TOKEN_TYPE_CLAIM': 'token_type',
        }
        
        # Add CORS settings to Django settings
        for setting in dir():
            if setting.startswith('CORS_'):
                setattr(settings, setting, globals()[setting])
