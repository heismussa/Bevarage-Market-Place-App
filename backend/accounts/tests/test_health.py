from rest_framework import status
from rest_framework.test import APITestCase


class HealthTests(APITestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})

    def test_schema_lists_auth_and_health(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode()
        self.assertIn("/api/v1/health/", body)
        self.assertIn("/api/v1/auth/register/", body)
        self.assertIn("/api/v1/auth/login/", body)
        self.assertIn("/api/v1/auth/refresh/", body)
        self.assertIn("/api/v1/auth/me/", body)
