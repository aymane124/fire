from pathlib import Path
import os
from datetime import timedelta
import pymysql
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure pymysql
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

# Secret Key
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-7#0vn+u!406sybobnmn6no(k!%&1u^fp2m7-ay47zm7(bz$#)s')

# Encryption keys
ENCRYPTION_KEY = Fernet.generate_key()
FERNET_KEY = os.getenv('FERNET_KEY', 'YII0pO-RDdZTxdGBg7HUQjVBGxVKxq7aWwM5Y9YHDWM=')
SSH_ENCRYPTION_KEY = os.getenv('SSH_ENCRYPTION_KEY', 'dGhpc2lzYXZlcnlsb25nc2VjcmV0a2V5Zm9yc3NoMTI=')

# Debug
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Allowed Hosts
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Installed Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_extensions',
    'auth_service.apps.AuthServiceConfig',
    'firewall_service.apps.FirewallServiceConfig',
    'datacenter_service.apps.DataCenterServiceConfig',
    'config_service.apps.ConfigServiceConfig',
    'command_service.apps.CommandServiceConfig',
    'analysis_service.apps.AnalysisServiceConfig',
    'camera_service',
    'template_service.apps.TemplateServiceConfig',
    'dailycheck_service',
    'history_service',
    "csp",
    'email_service',
    'interface_monitor_service.apps.InterfaceMonitorServiceConfig',

    'websocket_service.apps.WebsocketServiceConfig',
    'dashboard_service.apps.DashboardServiceConfig',
    'screenshot_service',
    'channels',
]

# Middleware
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auth_service.middleware.RateLimitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auth_service.middleware.SecurityHeadersMiddleware',
]

# Only add CSP middleware in production
if not DEBUG:
    MIDDLEWARE.append("csp.middleware.CSPMiddleware")

ROOT_URLCONF = 'firewallbackend.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'static')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'firewallbackend.wsgi.application'
ASGI_APPLICATION = 'firewallbackend.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'auth_service.User'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
]

EMAIL_APP_KEY_1 = os.environ.get('EMAIL_APP_KEY_1', '')
EMAIL_APP_KEY_2 = os.environ.get('EMAIL_APP_KEY_2', '')
EMAIL_APP_KEY_3 = os.environ.get('EMAIL_APP_KEY_3', '')


# CSRF Cookies
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = None
CSRF_USE_SESSIONS = False
CSRF_COOKIE_DOMAIN = None
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

# Sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_METHODS = ['DELETE','GET','OPTIONS','PATCH','POST','PUT']
CORS_ALLOW_HEADERS = [
    'accept','accept-encoding','authorization','content-type','dnt',
    'origin','user-agent','x-csrftoken','x-requested-with',
]
CORS_EXPOSE_HEADERS = ['content-type','x-csrftoken']
CORS_PREFLIGHT_MAX_AGE = 86400
CORS_ALLOW_PRIVATE_NETWORK = True

# Security
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# SSL Certificate paths (optional, if needed)
SSL_CERTIFICATE = os.path.join(BASE_DIR, 'certs', 'cert.pem')
SSL_PRIVATE_KEY = os.path.join(BASE_DIR, 'certs', 'key.pem')

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Content Security Policy
if DEBUG:
    # More permissive CSP for development
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ("'self'", "'unsafe-inline'", "'unsafe-eval'"),
            'script-src': (
                "'self'",
                "'unsafe-eval'",
                "'unsafe-inline'",
                "blob:",
            ),
            'style-src': (
                "'self'",
                "'unsafe-inline'",
                "https://cdnjs.cloudflare.com",
                "https://unpkg.com",
            ),
            'img-src': (
                "'self'",
                "data:",
                "blob:",
                "https://*.basemaps.cartocdn.com",
                "https://*.tile.openstreetmap.org",
                "https://tile.openstreetmap.org",
                "https://*.cartocdn.com",
                "https://*.carto.com",
                "https://cdnjs.cloudflare.com",
            ),
            'connect-src': (
                "'self'",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "ws://localhost:8000",
                "ws://127.0.0.1:8000",
                "https://*.basemaps.cartocdn.com",
                "http://localhost:8000/api/",
                "http://127.0.0.1:8000/api/",
            ),
            'font-src': (
                "'self'",
                "data:",
                "https://cdnjs.cloudflare.com",
            ),
            'media-src': ("'self'",),
            'object-src': ("'none'",),
            'base-uri': ("'self'",),
            'form-action': ("'self'",),
            'frame-ancestors': ("'none'",),
            'frame-src': ("'none'",),
            'manifest-src': ("'self'",),
        }
    }
else:
    # Stricter CSP for production
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ("'self'",),
            'script-src': (
                "'self'",
                "'unsafe-eval'",
                "'unsafe-inline'",
                "blob:",
            ),
            'style-src': (
                "'self'",
                "'unsafe-inline'",
                "https://cdnjs.cloudflare.com",
                "https://unpkg.com",
            ),
            'img-src': (
                "'self'",
                "data:",
                "blob:",
                "https://*.basemaps.cartocdn.com",
                "https://*.tile.openstreetmap.org",
                "https://tile.openstreetmap.org",
                "https://*.cartocdn.com",
                "https://*.carto.com",
                "https://cdnjs.cloudflare.com",
            ),
            'connect-src': (
                "'self'",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "ws://localhost:8000",
                "ws://127.0.0.1:8000",
                "https://*.basemaps.cartocdn.com",
                "http://localhost:8000/api/",
                "http://127.0.0.1:8000/api/",
            ),
            'font-src': (
                "'self'",
                "data:",
                "https://cdnjs.cloudflare.com",
            ),
            'media-src': ("'self'",),
            'object-src': ("'none'",),
            'base-uri': ("'self'",),
            'form-action': ("'self'",),
            'frame-ancestors': ("'none'",),
            'frame-src': ("'none'",),
            'manifest-src': ("'self'",),
        }
    }

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'aymanekhaliiss23@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'jvobgqgyxduxipwz')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'aymanekhaliiss23@gmail.com')

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
