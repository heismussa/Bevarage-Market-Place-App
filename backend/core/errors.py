"""Stable, machine-readable error codes and the domain exception that carries them.

Every API error body has the shape:
    {"error": {"code": "SOME_CODE", "message": "...", "details": {}}}

Codes are part of the public contract. Add new ones; never rename or reuse them.
"""

from enum import StrEnum

from rest_framework import status
from rest_framework.exceptions import APIException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_INVALID = "TOKEN_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_ACCEPTABLE = "NOT_ACCEPTABLE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    THROTTLED = "THROTTLED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CART_STORE_CONFLICT = "CART_STORE_CONFLICT"
    PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE"
    STORE_CLOSED = "STORE_CLOSED"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    EMPTY_CART = "EMPTY_CART"
    INVALID_TRANSITION = "INVALID_TRANSITION"


def error_payload(code, message, details=None):
    return {
        "error": {
            "code": str(code),
            "message": str(message),
            "details": details or {},
        }
    }


class ApiError(APIException):
    """Raise from services or views to return a specific error code.

    Example:
        raise ApiError(ErrorCode.CONFLICT, "Cart has items from another store.",
                       status_code=409, details={"store_id": 3})
    """

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code, message, *, status_code=None, details=None):
        self.code = str(code)
        self.message = str(message)
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=self.message, code=self.code)
