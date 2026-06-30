import time
import logging
from collections import defaultdict
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache

logger = logging.getLogger('nyayasaathi.middleware')


class RateLimitMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = getattr(settings, 'RATE_LIMITS', {})
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        super().__init__(get_response)

    def process_request(self, request):
        if not self.enabled:
            return None

        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None

        client_ip = self.get_client_ip(request)
        path = request.path
        method = request.method

        limit_key = self.get_limit_key(path, method)
        if not limit_key:
            return None

        limit_config = self.rate_limits.get(limit_key)
        if not limit_config:
            limit_config = self.rate_limits.get('default', {'requests': 100, 'window': 3600})

        cache_key = f"ratelimit:{limit_key}:{client_ip}"
        current_count = cache.get(cache_key, 0)

        if current_count >= limit_config['requests']:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on {path} "
                f"({current_count}/{limit_config['requests']} requests)"
            )
            return JsonResponse(
                {
                    'status': 'error',
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': limit_config['window'],
                },
                status=429,
                headers={
                    'Retry-After': str(limit_config['window']),
                    'X-RateLimit-Limit': str(limit_config['requests']),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(int(time.time()) + limit_config['window']),
                }
            )

        cache.set(cache_key, current_count + 1, limit_config['window'])

        request.META['HTTP_X_RATELIMIT_LIMIT'] = str(limit_config['requests'])
        request.META['HTTP_X_RATELIMIT_REMAINING'] = str(
            max(0, limit_config['requests'] - current_count - 1)
        )
        request.META['HTTP_X_RATELIMIT_RESET'] = str(int(time.time()) + limit_config['window'])

        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def get_limit_key(self, path, method):
        if path == '/api/search/' and method == 'POST':
            return 'search'
        elif path == '/api/classify/' and method == 'POST':
            return 'classify'
        elif path.startswith('/api/auth/'):
            return 'auth'
        elif path.startswith('/api/'):
            return 'api'
        return 'default'