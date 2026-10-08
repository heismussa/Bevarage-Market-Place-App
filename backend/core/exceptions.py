import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback
from rest_framework_simplejwt.exceptions import InvalidToken

from core.errors import ApiError, ErrorCode, error_payload

logger = logging.getLogger(__name__)

# Order matters: subclasses must come before their parents.
_CODE_BY_EXCEPTION = (
    (exceptions.ValidationError, ErrorCode.VALIDATION_ERROR),
    (exceptions.ParseError, ErrorCode.PARSE_ERROR),
    (InvalidToken, ErrorCode.TOKEN_INVALID),
    (exceptions.NotAuthenticated, ErrorCode.NOT_AUTHENTICATED),
    (exceptions.AuthenticationFailed, ErrorCode.AUTHENTICATION_FAILED),
    (exceptions.PermissionDenied, ErrorCode.PERMISSION_DENIED),
    (exceptions.NotFound, ErrorCode.NOT_FOUND),
    (exceptions.MethodNotAllowed, ErrorCode.METHOD_NOT_ALLOWED),
    (exceptions.NotAcceptable, ErrorCode.NOT_ACCEPTABLE),
    (exceptions.UnsupportedMediaType, ErrorCode.UNSUPPORTED_MEDIA_TYPE),
    (exceptions.Throttled, ErrorCode.THROTTLED),
)


def api_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER that renders every error in the shared format."""
    exc = _to_drf_exception(exc)
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        set_rollback()
        return Response(
            error_payload(ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code, message, details = _describe(exc, response.data)
    response.data = error_payload(code, message, details)
    return response


def _to_drf_exception(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            return exceptions.ValidationError(exc.message_dict)
        return exceptions.ValidationError({"non_field_errors": exc.messages})
    if isinstance(exc, Http404):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied()
    return exc


def _describe(exc, data):
    if isinstance(exc, ApiError):
        return exc.code, exc.message, exc.details

    code = _code_for(exc)

    if isinstance(exc, exceptions.ValidationError):
        details = data if isinstance(data, dict) else {"non_field_errors": data}
        return code, _first_message(details) or "Invalid input.", details

    message = data.get("detail", "") if isinstance(data, dict) else data
    details = {}
    if isinstance(exc, exceptions.Throttled) and exc.wait is not None:
        details = {"wait_seconds": int(exc.wait)}
    return code, str(message), details


def _code_for(exc):
    for exception_class, code in _CODE_BY_EXCEPTION:
        if isinstance(exc, exception_class):
            return code
    if exc.status_code == status.HTTP_409_CONFLICT:
        return ErrorCode.CONFLICT
    return str(getattr(exc, "default_code", "error")).upper()


def _first_message(value):
    if isinstance(value, dict):
        for item in value.values():
            found = _first_message(item)
            if found:
                return found
    elif isinstance(value, list | tuple):
        for item in value:
            found = _first_message(item)
            if found:
                return found
    elif value:
        return str(value)
    return None
