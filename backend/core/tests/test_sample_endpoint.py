"""Exercises the shared helpers and the error format through a real endpoint (/auth/me/)."""

from rest_framework import status
from rest_framework.test import APIClient

from core.errors import ErrorCode
from core.testing.api import ApiTestCase

ME_URL = "/api/v1/auth/me/"


class SampleEndpointTests(ApiTestCase):
    def test_role_clients_are_authenticated(self):
        customer_client, customer = self.customer_client(full_name="Amina Hassan")
        owner_client, owner = self.store_owner_client()
        admin_client, admin = self.admin_client()

        for client, phone, role in (
            (customer_client, customer.user.phone, "CUSTOMER"),
            (owner_client, owner.user.phone, "STORE_OWNER"),
            (admin_client, admin.phone, "ADMIN"),
        ):
            response = client.get(ME_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["phone"], phone)
            self.assertEqual(response.data["role"], role)

    def test_missing_token(self):
        self.assertError(
            APIClient().get(ME_URL),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.NOT_AUTHENTICATED,
        )

    def test_invalid_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        self.assertError(client.get(ME_URL), status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID)

    def test_method_not_allowed(self):
        client, _customer = self.customer_client()

        self.assertError(
            client.put(ME_URL, {"full_name": "X"}, format="json"),
            status.HTTP_405_METHOD_NOT_ALLOWED,
            ErrorCode.METHOD_NOT_ALLOWED,
        )

    def test_validation_error_lists_fields(self):
        client, _customer = self.customer_client()

        error = self.assertError(
            client.patch(ME_URL, {"phone": "0712345678"}, format="json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("phone", error["details"])
        self.assertIn("+255", error["message"])

    def test_malformed_json(self):
        client, _customer = self.customer_client()

        self.assertError(
            client.patch(ME_URL, data="{bad json", content_type="application/json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.PARSE_ERROR,
        )

    def test_wrong_password(self):
        _client, customer = self.customer_client()

        self.assertError(
            APIClient().post(
                "/api/v1/auth/login/",
                {"phone": customer.user.phone, "password": "wrong-password"},
                format="json",
            ),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHENTICATION_FAILED,
        )

    def test_unknown_api_route_is_json_404(self):
        self.assertError(
            APIClient().get("/api/v1/does-not-exist/"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
