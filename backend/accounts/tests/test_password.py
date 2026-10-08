import re
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts import password_services
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import TEST_PASSWORD, UserFactory

RESET_URL = "/api/v1/auth/password/reset/"
CONFIRM_URL = "/api/v1/auth/password/reset/confirm/"
CHANGE_URL = "/api/v1/auth/password/change/"
NEW_PASSWORD = "Maji-Safi-Kabisa-2026"


class PasswordTestCase(ApiTestCase):
    def setUp(self):
        cache.clear()
        self.user = UserFactory()
        self.anonymous = APIClient()

    def login(self, password=TEST_PASSWORD):
        return self.anonymous.post(
            "/api/v1/auth/login/", {"phone": self.user.phone, "password": password}, format="json"
        )

    def logged_in_client(self):
        tokens = self.login().data
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return client, tokens

    def request_code(self, phone=None):
        with self.assertLogs("accounts.sms", "WARNING") as logs:
            response = self.anonymous.post(
                RESET_URL, {"phone": phone or self.user.phone}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return re.search(r"code is (\d{6})", logs.output[0]).group(1)

    def confirm(self, code, password=NEW_PASSWORD, phone=None):
        return self.anonymous.post(
            CONFIRM_URL,
            {"phone": phone or self.user.phone, "code": code, "new_password": password},
            format="json",
        )


class PasswordResetTests(PasswordTestCase):
    def test_reset_with_sms_code(self):
        code = self.request_code()

        response = self.confirm(code)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.login(NEW_PASSWORD).status_code, status.HTTP_200_OK)
        self.assertError(
            self.login(), status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTHENTICATION_FAILED
        )

    def test_reset_ends_every_existing_login(self):
        client, tokens = self.logged_in_client()
        self.assertEqual(client.get("/api/v1/auth/me/").status_code, status.HTTP_200_OK)

        self.confirm(self.request_code())

        self.assertError(
            client.get("/api/v1/auth/me/"), status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID
        )
        self.assertError(
            self.anonymous.post(
                "/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
            ),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID,
        )

    def test_code_works_once(self):
        code = self.request_code()
        self.confirm(code)

        error = self.assertError(
            self.confirm(code, "Another-Strong-Pass-99"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("code", error["details"])

    def test_wrong_or_expired_code(self):
        code = self.request_code()
        wrong = f"{(int(code) + 1) % 1_000_000:06d}"

        self.assertError(
            self.confirm(wrong), status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR
        )
        with mock.patch("accounts.password_services.time.time", return_value=10**10):
            self.assertError(
                self.confirm(code), status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR
            )
        self.assertEqual(self.login().status_code, status.HTTP_200_OK)

    def test_code_from_previous_window_still_works(self):
        window = 1_000_000
        code = password_services.reset_code(self.user, window)
        minutes = 10
        later = (window + 1) * minutes * 60 + 5

        with (
            override_settings(PASSWORD_RESET_CODE_MINUTES=minutes),
            mock.patch("accounts.password_services.time.time", return_value=later),
        ):
            response = self.confirm(code)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_weak_new_password_is_rejected(self):
        error = self.assertError(
            self.confirm(self.request_code(), "123"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("new_password", error["details"])

    def test_unknown_phone_gets_the_same_answer_and_no_sms(self):
        with self.assertNoLogs("accounts.sms", "WARNING"):
            response = self.anonymous.post(RESET_URL, {"phone": "+255799999999"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("If this phone number is registered", response.data["detail"])

    def test_inactive_user_gets_no_code(self):
        self.user.is_active = False
        self.user.save()

        with self.assertNoLogs("accounts.sms", "WARNING"):
            self.anonymous.post(RESET_URL, {"phone": self.user.phone}, format="json")

    @override_settings(PASSWORD_RESET_REQUEST_RATE="2/hour")
    def test_requests_are_limited_per_phone(self):
        self.request_code()
        self.request_code()

        self.assertError(
            self.anonymous.post(RESET_URL, {"phone": self.user.phone}, format="json"),
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.THROTTLED,
        )

    @override_settings(PASSWORD_RESET_CONFIRM_RATE="3/hour")
    def test_guesses_are_limited_per_phone(self):
        for _ in range(3):
            self.confirm("000000")

        self.assertError(
            self.confirm(self.request_code()),
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.THROTTLED,
        )


class PasswordChangeTests(PasswordTestCase):
    def test_change_returns_new_tokens_and_logs_out_other_devices(self):
        this_device, _ = self.logged_in_client()
        other_device, _ = self.logged_in_client()

        response = this_device.post(
            CHANGE_URL,
            {"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(set(response.data), {"access", "refresh"})
        fresh = APIClient()
        fresh.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(fresh.get("/api/v1/auth/me/").status_code, status.HTTP_200_OK)
        self.assertError(
            other_device.get("/api/v1/auth/me/"),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID,
        )
        self.assertEqual(self.login(NEW_PASSWORD).status_code, status.HTTP_200_OK)

    def test_wrong_current_password(self):
        client, _ = self.logged_in_client()

        error = self.assertError(
            client.post(
                CHANGE_URL,
                {"current_password": "not-it", "new_password": NEW_PASSWORD},
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("current_password", error["details"])

    def test_requires_login(self):
        self.assertError(
            self.anonymous.post(CHANGE_URL, {}, format="json"),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.NOT_AUTHENTICATED,
        )
