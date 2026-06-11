import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('nyayasaathi.middleware')


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if hasattr(settings, 'SECURE_HSTS_SECONDS') and settings.SECURE_HSTS_SECONDS and not settings.DEBUG:
            response['Strict-Transport-Security'] = (
                f'max-age={settings.SECURE_HSTS_SECONDS}; '
                f'includeSubDomains; preload'
            )

        response['X-Frame-Options'] = getattr(settings, 'X_FRAME_OPTIONS', 'DENY')
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = getattr(
            settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin'
        )
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        response['Cross-Origin-Opener-Policy'] = getattr(
            settings, 'SECURE_CROSS_ORIGIN_OPENER_POLICY', 'same-origin'
        )
        response['Cross-Origin-Embedder-Policy'] = getattr(
            settings, 'SECURE_CROSS_ORIGIN_EMBEDDER_POLICY', 'require-corp'
        )

        if hasattr(settings, 'SECURE_CONTENT_SECURITY_POLICY') and settings.SECURE_CONTENT_SECURITY_POLICY:
            response['Content-Security-Policy'] = settings.SECURE_CONTENT_SECURITY_POLICY

        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        server_header = response.get('Server')
        if server_header:
            del response['Server']

        x_powered_by = response.get('X-Powered-By')
        if x_powered_by:
            del response['X-Powered-By']

        return response