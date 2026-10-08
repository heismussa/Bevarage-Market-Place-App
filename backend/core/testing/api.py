import json

from rest_framework.test import APIClient, APITestCase

from accounts.tokens import SessionRefreshToken
from core.testing.factories import AdminUserFactory, CustomerFactory, StoreOwnerFactory


def authenticated_client(user):
    """APIClient that sends a real JWT access token for user."""
    client = APIClient()
    token = SessionRefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _user_overrides(user_kwargs):
    return {f"user__{key}": value for key, value in user_kwargs.items()}


class ApiTestCase(APITestCase):
    """APITestCase with one-line authenticated clients per role and error assertions."""

    def customer_client(self, **user_kwargs):
        """Return (client, Customer profile)."""
        customer = CustomerFactory(**_user_overrides(user_kwargs))
        return authenticated_client(customer.user), customer

    def store_owner_client(self, **user_kwargs):
        """Return (client, StoreOwner profile)."""
        owner = StoreOwnerFactory(**_user_overrides(user_kwargs))
        return authenticated_client(owner.user), owner

    def admin_client(self, **user_kwargs):
        """Return (client, admin User)."""
        admin = AdminUserFactory(**user_kwargs)
        return authenticated_client(admin), admin

    def assertError(self, response, status_code, code):
        """Assert the shared error format and return the inner error object."""
        self.assertEqual(response.status_code, status_code, response.content)
        body = json.loads(response.content)
        self.assertEqual(set(body), {"error"}, body)
        error = body["error"]
        self.assertEqual(set(error), {"code", "message", "details"}, error)
        self.assertEqual(error["code"], str(code), error)
        self.assertIsInstance(error["message"], str)
        self.assertIsInstance(error["details"], dict)
        return error
