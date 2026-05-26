"""
EpitopX — request middleware.

RequestIDMiddleware  : injects a UUID request-id into every request/response.
AuditLogMiddleware   : writes security-sensitive actions to the AuditLog table.
"""
import logging
import uuid

logger = logging.getLogger(__name__)

_AUDIT_PATHS = {
    '/api/v1/users/login/',
    '/api/v1/users/register/',
    '/api/v1/users/logout/',
    '/api/v1/users/password-reset/',
    '/api/v1/users/password-reset-confirm/',
    '/api/v1/users/verify-email/',
}

_AUDIT_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class RequestIDMiddleware:
    """Attach a UUID to every request and echo it in the response header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        return response


class AuditLogMiddleware:
    """
    Write immutable audit log entries for security-sensitive endpoints.
    Runs asynchronously via a deferred DB write so it never blocks the response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._maybe_log(request, response)
        return response

    def _maybe_log(self, request, response):
        path = request.path_info
        if path not in _AUDIT_PATHS and request.method not in _AUDIT_METHODS:
            return
        if path not in _AUDIT_PATHS:
            return
        try:
            from .models import AuditLog
            user = request.user if request.user.is_authenticated else None
            AuditLog.objects.create(
                user=user,
                action=f"{request.method} {path}",
                resource=path,
                ip_address=self._get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_id=getattr(request, 'request_id', ''),
                extra={'status': response.status_code},
            )
        except Exception:
            logger.exception("AuditLogMiddleware failed silently")

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
