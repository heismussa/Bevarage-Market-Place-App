"""OpenAPI helpers so every endpoint documents the shared error format."""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers

from core.errors import ErrorCode, error_payload


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorBodySerializer()


def error_response(description, code, message, details=None):
    return OpenApiResponse(
        response=ErrorResponseSerializer,
        description=description,
        examples=[
            OpenApiExample(
                str(code),
                value=error_payload(code, message, details),
                response_only=True,
            )
        ],
    )


_STANDARD = {
    400: (
        "Invalid input",
        ErrorCode.VALIDATION_ERROR,
        "This field is required.",
        {"field": ["This field is required."]},
    ),
    401: (
        "Missing or invalid credentials",
        ErrorCode.NOT_AUTHENTICATED,
        "Authentication credentials were not provided.",
        None,
    ),
    403: (
        "Role not allowed",
        ErrorCode.PERMISSION_DENIED,
        "You do not have permission to perform this action.",
        None,
    ),
    404: (
        "Not found or not visible to this user",
        ErrorCode.NOT_FOUND,
        "No object matches the given query.",
        None,
    ),
    409: (
        "Conflicts with current state",
        ErrorCode.CONFLICT,
        "The request conflicts with the current state.",
        None,
    ),
    429: ("Rate limited", ErrorCode.THROTTLED, "Request was throttled.", {"wait_seconds": 30}),
}


def standard_errors(*status_codes):
    """Return {status: OpenApiResponse} for the given status codes."""
    return {status_code: error_response(*_STANDARD[status_code]) for status_code in status_codes}
