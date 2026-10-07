from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Customer, StoreOwner, UserRole
from accounts.tests.factories import PASSWORD, create_user


class AuthApiTests(APITestCase):
    def test_phone_login_returns_tokens(self):
        create_user("+255712345690", UserRole.CUSTOMER, full_name="John Mushi")

        response = self.client.post(
            "/api/v1/auth/login/",
            {"phone": "+255712345690", "password": PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_is_rejected(self):
        create_user("+255712345691", UserRole.CUSTOMER)

        response = self.client.post(
            "/api/v1/auth/login/",
            {"phone": "+255712345691", "password": "not-the-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_a_new_access_token(self):
        create_user("+255712345692", UserRole.CUSTOMER)
        login = self.client.post(
            "/api/v1/auth/login/",
            {"phone": "+255712345692", "password": PASSWORD},
            format="json",
        )

        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_register_rejects_admin_and_driver(self):
        for role, phone in (("ADMIN", "+255712345693"), ("DRIVER", "+255712345694")):
            response = self.client.post(
                "/api/v1/auth/register/",
                {
                    "full_name": "Blocked Role",
                    "phone": phone,
                    "password": PASSWORD,
                    "role": role,
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, role)

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(StoreOwner.objects.count(), 0)

    def test_register_customer_creates_a_profile(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "full_name": "Amina Hassan",
                "phone": "+255712345695",
                "password": PASSWORD,
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_me_cannot_change_role_or_staff(self):
        create_user("+255712345697", UserRole.CUSTOMER, full_name="John Mushi")
        login = self.client.post(
            "/api/v1/auth/login/",
            {"phone": "+255712345697", "password": PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"full_name": "Updated Name", "role": "ADMIN", "is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["role"], "CUSTOMER")
        self.assertFalse(response.data["is_staff"])
