import json
import logging
import re
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('nyayasaathi.middleware')

MAX_REQUEST_SIZE = 1024 * 1024
MAX_JSON_DEPTH = 10
MAX_JSON_KEYS = 100
MAX_STRING_LENGTH = 10000

DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'eval\s*\(',
    r'document\.',
    r'window\.',
    r'alert\s*\(',
    r'confirm\s*\(',
    r'prompt\s*\(',
    r'expression\s*\(',
    r'vbscript:',
    r'data:text/html',
    r'<iframe',
    r'<object',
    r'<embed',
    r'<form',
    r'<input',
    r'SELECT.*FROM',
    r'UNION.*SELECT',
    r'DROP\s+TABLE',
    r'DELETE\s+FROM',
    r'INSERT\s+INTO',
    r'UPDATE\s+SET',
    r'OR\s+1\s*=\s*1',
    r';\s*--',
    r'/\*.*\*/',
    r'xp_cmdshell',
    r'sp_executesql',
    r'EXEC\s*\(',
    r'EXECUTE\s*\(',
]

COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


class RequestValidationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, 'REQUEST_VALIDATION_ENABLED', True):
            return None

        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None

        content_length = request.META.get('CONTENT_LENGTH')
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            logger.warning(f"Request too large: {content_length} bytes from {self.get_client_ip(request)}")
            return JsonResponse(
                {'status': 'error', 'error': 'Request entity too large'},
                status=413
            )

        if request.content_type == 'application/json' and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                validation_error = self.validate_json(data)
                if validation_error:
                    logger.warning(
                        f"Invalid JSON payload from {self.get_client_ip(request)}: {validation_error}"
                    )
                    return JsonResponse(
                        {'status': 'error', 'error': validation_error},
                        status=400
                    )
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {self.get_client_ip(request)}")
                return JsonResponse(
                    {'status': 'error', 'error': 'Invalid JSON payload'},
                    status=400
                )

        for key, value in request.GET.items():
            if self.contains_dangerous_content(str(value)):
                logger.warning(
                    f"Dangerous content in query param '{key}' from {self.get_client_ip(request)}"
                )
                return JsonResponse(
                    {'status': 'error', 'error': 'Invalid request parameters'},
                    status=400
                )

        return None

    def validate_json(self, obj, depth=0, key_count=0):
        if depth > MAX_JSON_DEPTH:
            return "JSON nesting too deep"

        if isinstance(obj, dict):
            if len(obj) > MAX_JSON_KEYS:
                return "Too many keys in JSON object"
            for key, value in obj.items():
                if not isinstance(key, str):
                    return "JSON keys must be strings"
                if len(key) > 100:
                    return "JSON key too long"
                if self.contains_dangerous_content(key):
                    return f"Dangerous content in key: {key}"
                error = self.validate_json(value, depth + 1, key_count + 1)
                if error:
                    return error
        elif isinstance(obj, list):
            if len(obj) > MAX_JSON_KEYS:
                return "Array too large"
            for item in obj:
                error = self.validate_json(item, depth + 1, key_count)
                if error:
                    return error
        elif isinstance(obj, str):
            if len(obj) > MAX_STRING_LENGTH:
                return "String value too long"
            if self.contains_dangerous_content(obj):
                return f"Dangerous content detected in string value"
        return None

    def contains_dangerous_content(self, text):
        if not isinstance(text, str):
            return False
        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')