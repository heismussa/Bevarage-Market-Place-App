from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Customer, StoreOwner
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import TEST_PASSWORD, UserFactory


class AuthApiTests(ApiTestCase):
    def login(self, phone, password=TEST_PASSWORD):
        return self.client.post(
            "/api/v1/auth/login/", {"phone": phone, "password": password}, format="json"
        )

    def test_phone_login_returns_tokens(self):
        user = UserFactory()

        response = self.login(user.phone)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_is_rejected(self):
        user = UserFactory()

        self.assertError(
            self.login(user.phone, "not-the-password"),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHENTICATION_FAILED,
        )

    def test_refresh_returns_a_new_access_token(self):
        user = UserFactory()
        refresh = self.login(user.phone).data["refresh"]

        response = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_register_rejects_admin_and_driver(self):
        for role, phone in (("ADMIN", "+255712345693"), ("DRIVER", "+255712345694")):
            response = self.client.post(
                "/api/v1/auth/register/",
                {
                    "full_name": "Blocked Role",
                    "phone": phone,
                    "password": TEST_PASSWORD,
                    "role": role,
                },
                format="json",
            )
            error = self.assertError(
                response, status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR
            )
            self.assertIn("role", error["details"])

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(StoreOwner.objects.count(), 0)

    def test_register_customer_creates_a_profile(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "full_name": "Amina Hassan",
                "phone": "+255712345695",
                "password": TEST_PASSWORD,
                "email": "amina@example.com",
                "role": "CUSTOMER",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "CUSTOMER")
        self.assertEqual(Customer.objects.count(), 1)
        self.assertNotIn("password", response.data)

    def test_register_rejects_a_weak_password(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "full_name": "Amina Hassan",
                "phone": "+255712345696",
                "password": "password",
                "role": "CUSTOMER",
            },
            format="json",
        )

        error = self.assertError(response, status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR)
        self.assertIn("password", error["details"])

    def test_me_cannot_change_role_or_staff(self):
        client, _customer = self.customer_client(full_name="John Mushi")

        response = client.patch(
            "/api/v1/auth/me/",
            {"full_name": "Updated Name", "role": "ADMIN", "is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["role"], "CUSTOMER")
        self.assertFalse(response.data["is_staff"])

    def test_me_requires_authentication(self):
        self.assertError(
            APIClient().get("/api/v1/auth/me/"),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.NOT_AUTHENTICATED,
        )
