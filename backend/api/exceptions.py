"""
EpitopX — global DRF exception handler.
Normalises all error responses to a consistent JSON envelope so the
frontend always receives the same shape regardless of the error source.
"""
import logging
import traceback

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Return a uniform error envelope:
        { "error": "<human message>", "code": "<machine code>", "details": {...} }
    """
    # Let DRF handle what it knows
    response = drf_exception_handler(exc, context)

    if response is not None:
        error_msg = _extract_message(response.data)
        response.data = {
            'error':   error_msg,
            'code':    _http_status_to_code(response.status_code),
            'details': response.data if isinstance(response.data, dict) else {},
        }
        return response

    # Unhandled exceptions — log full traceback, return 500 with generic message
    request = context.get('request')
    rid = getattr(request, 'request_id', '-')
    logger.error(
        "Unhandled exception [rid=%s]: %s\n%s",
        rid, exc, traceback.format_exc()
    )

    return Response(
        {
            'error':   'An internal server error occurred.',
            'code':    'server_error',
            'details': {},
            'request_id': rid,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_message(data):
    if isinstance(data, dict):
        for key in ('detail', 'error', 'message', 'non_field_errors'):
            if key in data:
                val = data[key]
                if isinstance(val, list) and val:
                    return str(val[0])
                return str(val)
        # First field error
        for val in data.values():
            if isinstance(val, list) and val:
                return str(val[0])
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)


def _http_status_to_code(http_status):
    mapping = {
        400: 'bad_request',
        401: 'unauthenticated',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        429: 'rate_limited',
        500: 'server_error',
    }
    return mapping.get(http_status, f'http_{http_status}')
