from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import exceptions, status

from core.errors import ApiError, ErrorCode
from core.exceptions import api_exception_handler

CONTEXT = {"view": None, "request": None}


class ExceptionHandlerTests(SimpleTestCase):
    def handle(self, exc):
        response = api_exception_handler(exc, CONTEXT)
        return response.status_code, response.data["error"]

    def test_api_error_keeps_code_status_and_details(self):
        status_code, error = self.handle(
            ApiError(
                "CART_STORE_CONFLICT",
                "Cart has items from another store.",
                status_code=status.HTTP_409_CONFLICT,
                details={"store_id": 3},
            )
        )

        self.assertEqual(status_code, 409)
        self.assertEqual(
            error,
            {
                "code": "CART_STORE_CONFLICT",
                "message": "Cart has items from another store.",
                "details": {"store_id": 3},
            },
        )

    def test_drf_validation_error_with_field_errors(self):
        status_code, error = self.handle(
            exceptions.ValidationError({"price": ["Ensure this value is greater than 0."]})
        )

        self.assertEqual(status_code, 400)
        self.assertEqual(error["code"], ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error["message"], "Ensure this value is greater than 0.")
        self.assertEqual(error["details"], {"price": ["Ensure this value is greater than 0."]})

    def test_drf_validation_error_with_a_list(self):
        _status, error = self.handle(exceptions.ValidationError(["Something is wrong."]))

        self.assertEqual(error["details"], {"non_field_errors": ["Something is wrong."]})

    def test_django_validation_error(self):
        status_code, error = self.handle(DjangoValidationError({"phone": ["Bad phone."]}))

        self.assertEqual(status_code, 400)
        self.assertEqual(error["code"], ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error["details"], {"phone": ["Bad phone."]})

    def test_http404(self):
        status_code, error = self.handle(Http404("hidden"))

        self.assertEqual(status_code, 404)
        self.assertEqual(error["code"], ErrorCode.NOT_FOUND)

    def test_throttled_includes_wait(self):
        status_code, error = self.handle(exceptions.Throttled(wait=12))

        self.assertEqual(status_code, 429)
        self.assertEqual(error["code"], ErrorCode.THROTTLED)
        self.assertEqual(error["details"], {"wait_seconds": 12})

    def test_unhandled_exception_becomes_internal_error(self):
        with self.assertLogs("core.exceptions", level="ERROR"):
            status_code, error = self.handle(RuntimeError("boom"))

        self.assertEqual(status_code, 500)
        self.assertEqual(error["code"], ErrorCode.INTERNAL_ERROR)
        self.assertNotIn("boom", error["message"])
