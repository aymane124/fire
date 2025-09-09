from corsheaders.defaults import default_headers
from corsheaders.defaults import default_methods

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = list(default_methods)
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-csrftoken',
    'x-requested-with',
]

CORS_EXPOSE_HEADERS = [
    'content-type',
    'x-csrftoken',
]

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

CORS_REPLACE_HTTPS_REFERER = True

CORS_URLS_REGEX = r'^/api/.*$'  # Only allow CORS for API endpoints 