from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs
import os
import django

# Get Django installation path
django_path = os.path.dirname(django.__file__)

# Collect all Django submodules
hiddenimports = collect_submodules('django')

# Remove GIS-related imports
hiddenimports = [imp for imp in hiddenimports if 'gis' not in imp.lower()]

# Add specific Django apps and modules
hiddenimports += [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.middleware',
    'django.template',
    'django.template.loaders',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'django.template.context_processors',
    'django.template.backends',
    'django.template.backends.django',
    'django.template.backends.jinja2',
    'django.db',
    'django.db.models',
    'django.db.models.fields',
    'django.db.models.fields.related',
    'django.db.models.fields.files',
    'django.db.models.fields.proxy',
    'django.db.models.fields.reverse_related',
    'django.db.models.fields.subclassing',
    'django.db.models.fields.related_descriptors',
    'django.db.models.fields.related_lookups',
    'django.db.models.fields.related_fields',
    'django.db.models.fields.related_models',
    'django.db.models.fields.related_objects',
    'django.db.models.fields.related_objects_descriptors',
    'django.db.models.fields.related_objects_fields',
    'django.db.models.fields.related_objects_lookups',
    'django.db.models.fields.related_objects_models',
    'django.db.models.fields.related_objects_objects',
    'django.db.models.fields.related_objects_querysets',
    'django.db.models.fields.related_objects_relations',
    'django.db.models.fields.related_objects_serializers',
    'django.db.models.fields.related_objects_views',
    'django.db.models.fields.related_objects_viewsets',
    'django.db.models.fields.related_objects_routers',
    'django.db.models.fields.related_objects_permissions',
    'django.db.models.fields.related_objects_authentication',
    'django.db.models.fields.related_objects_tokens',
    'django.db.models.fields.related_objects_middleware',
    'django.db.models.fields.related_objects_context_processors',
    'django.db.models.fields.related_objects_templates',
    'django.db.models.fields.related_objects_static',
    'django.db.models.fields.related_objects_media',
    'django.db.models.fields.related_objects_admin',
    'django.db.models.fields.related_objects_auth',
    'django.db.models.fields.related_objects_contenttypes',
    'django.db.models.fields.related_objects_sessions',
    'django.db.models.fields.related_objects_messages',
    'django.db.models.fields.related_objects_staticfiles',
    'django.db.models.fields.related_objects_sites',
]

# Collect all data files from Django
datas = collect_data_files('django')

# Add specific Django data files with correct paths
datas += [
    (os.path.join(django_path, 'contrib/admin/static/admin'), 'django/contrib/admin/static/admin'),
    (os.path.join(django_path, 'contrib/admin/templates/admin'), 'django/contrib/admin/templates/admin'),
]

# Add your project's static and template files
datas += [
    ('static', 'static'),
    ('templates', 'templates'),
    ('staticfiles', 'staticfiles'),
    
]

# Add your custom apps and their data files
datas += [
    ('firewall_service', 'firewall_service'),
    ('datacenter_service', 'datacenter_service'),
    ('config_service', 'config_service'),
    ('command_service', 'command_service'),
    ('camera_service', 'camera_service'),
    ('auth_service', 'auth_service'),
    ('analysis_service', 'analysis_service'),
    ('template_service', 'template_service'),
    ('dailycheck_service', 'dailycheck_service'),
    ('dashboard_service', 'dashboard_service'),
    ('history_service', 'history_service'),
]

# Collect all dynamic libraries from Django
binaries = collect_dynamic_libs('django')

# Add specific Django binaries
binaries += []

# Add Django settings module
hiddenimports += ['django.conf']

# Add Django template loaders
hiddenimports += [
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
]

# Add Django static files finders
hiddenimports += [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Add Django middleware
hiddenimports += [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

# Add WhiteNoise
hiddenimports += [
    'whitenoise',
    'whitenoise.middleware',
    'whitenoise.storage',
    'whitenoise.django',
]

# Add Django REST framework
hiddenimports += [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework.authentication',
    'rest_framework.permissions',
    'rest_framework.views',
    'rest_framework.viewsets',
    'rest_framework.routers',
    'rest_framework.serializers',
    'rest_framework.filters',
    'rest_framework.pagination',
    'rest_framework.response',
    'rest_framework.request',
    'rest_framework.status',
    'rest_framework.decorators',
    'rest_framework.mixins',
    'rest_framework.generics',
    'rest_framework.parsers',
    'rest_framework.parsers.JSONParser',
    'rest_framework.parsers.FormParser',
    'rest_framework.parsers.MultiPartParser',
    'rest_framework.parsers.FileUploadParser',
    'rest_framework.renderers',
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
    'rest_framework.renderers.AdminRenderer',
    'rest_framework.renderers.TemplateHTMLRenderer',
    'rest_framework.renderers.StaticHTMLRenderer',
    'rest_framework.renderers.MultiPartRenderer',
    'rest_framework.renderers.HTMLFormRenderer',
    'rest_framework.renderers.TemplateRenderer',
    'rest_framework.negotiation',
    'rest_framework.negotiation.DefaultContentNegotiation',
]

# Add JWT
hiddenimports += [
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.authentication',
    'rest_framework_simplejwt.tokens',
    'rest_framework_simplejwt.views',
]

# Add CORS
hiddenimports += [
    'corsheaders',
    'corsheaders.middleware',
]

# Add Django Filter
hiddenimports += [
    'django_filters',
    'django_filters.rest_framework',
]

# Add CSP
hiddenimports += [
    'csp',
    'csp.middleware',
]

# Add your custom apps and their configurations
hiddenimports += [
    'firewall_service',
    'firewall_service.apps',
    'firewall_service.models',
    'firewall_service.views',
    'firewall_service.urls',
    'firewall_service.serializers',
    'firewall_service.admin',
    
    'datacenter_service',
    'datacenter_service.apps',
    'datacenter_service.models',
    'datacenter_service.views',
    'datacenter_service.urls',
    'datacenter_service.serializers',
    'datacenter_service.admin',
    
    'config_service',
    'config_service.apps',
    'config_service.models',
    'config_service.views',
    'config_service.urls',
    'config_service.serializers',
    'config_service.admin',
    
    'command_service',
    'command_service.apps',
    'command_service.models',
    'command_service.views',
    'command_service.urls',
    'command_service.serializers',
    'command_service.admin',
    
    'camera_service',
    'camera_service.apps',
    'camera_service.models',
    'camera_service.views',
    'camera_service.urls',
    'camera_service.serializers',
    'camera_service.admin',
    
    'auth_service',
    'auth_service.apps',
    'auth_service.models',
    'auth_service.views',
    'auth_service.urls',
    'auth_service.serializers',
    'auth_service.admin',
    
    'analysis_service',
    'analysis_service.apps',
    'analysis_service.models',
    'analysis_service.views',
    'analysis_service.urls',
    'analysis_service.serializers',
    'analysis_service.admin',
    
    'template_service',
    'template_service.apps',
    'template_service.models',
    'template_service.views',
    'template_service.urls',
    'template_service.serializers',
    'template_service.admin',
    
    'dailycheck_service',
    'dailycheck_service.apps',
    'dailycheck_service.models',
    'dailycheck_service.views',
    'dailycheck_service.urls',
    'dailycheck_service.serializers',
    'dailycheck_service.admin',

    'dashboard_service',
    'dashboard_service.apps',
    'dashboard_service.models',
    'dashboard_service.views',
    'dashboard_service.urls',
    'dashboard_service.serializers',
    'dashboard_service.admin',

    'history_service',
    'history_service.apps',
    'history_service.models',
    'history_service.views',
    'history_service.urls',
    'history_service.serializers',
    'history_service.admin',
]

# Add additional dependencies from requirements.txt
hiddenimports += [
    'pymysql',
    'python_dotenv',
    'gunicorn',
    'whitenoise',
    'ipaddress',
    'paramiko',
    'pythonping',
    'waitress',
    'cryptography',
    'cryptography.fernet',
    'pandas',
    'xlsxwriter',
    'jinja2',
    'psycopg2',
    'setuptools',
    'django_extensions',
] 