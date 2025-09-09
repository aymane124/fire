from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
import time
import logging
import base64
import json

logger = logging.getLogger(__name__)

class CustomCorsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add CORS headers to all responses
        if request.method == 'OPTIONS':
            response = HttpResponse()
            origin = request.headers.get('origin', 'http://localhost:5173')
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
            return response
        return None

    def process_response(self, request, response):
        # Add CORS headers to all responses
        origin = request.headers.get('origin', 'http://localhost:5173')
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Add comprehensive security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        # Only add CSP in production
        from django.conf import settings
        if not settings.DEBUG:
            response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';"
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip rate limiting for certain paths
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None

        def get_jwt_user_id(request):
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload_part = token.split('.')[1]
                    rem = len(payload_part) % 4
                    if rem > 0:
                        payload_part += '=' * (4 - rem)
                    payload = json.loads(base64.urlsafe_b64decode(payload_part.encode()).decode())
                    return payload.get('user_id')
                except Exception as e:
                    logger.warning(f"JWT decode error: {e}")
            return None

        # Get IP address for all requests (even authenticated ones)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        user_id = get_jwt_user_id(request)
        if user_id:
            rate_key = f"rate_limit_user_{user_id}"
        else:
            rate_key = f"rate_limit_ip_{ip}"
        logger.warning(f"[RateLimit] key={rate_key} user_id={user_id} path={request.path}")

        # Get current rate limit data
        rate_data = cache.get(rate_key, {'count': 0, 'reset_time': time.time() + 60})
        
        # Check if rate limit window has expired
        if time.time() > rate_data['reset_time']:
            rate_data = {'count': 0, 'reset_time': time.time() + 420}
        
        # Increment request count
        rate_data['count'] += 1
        
        # Check if rate limit exceeded
        if rate_data['count'] > 60:  # 60 requests per minute (plus sécurisé)
            logger.warning(f"Rate limit exceeded for IP: {ip} (user_id: {user_id})")
            return HttpResponse(
                'Rate limit exceeded. Please try again later.',
                status=429
            )
        
        # Update rate limit data
        cache.set(rate_key, rate_data, 60)
        return None 