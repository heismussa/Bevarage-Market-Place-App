from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class PhoneRateThrottle(SimpleRateThrottle):
    """Limits requests per phone number in the body, whoever sends them.

    The cache must be shared by all server processes for the limit to hold.
    """

    setting_name = None

    def get_rate(self):
        return getattr(settings, self.setting_name)

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip()
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": phone}


class PasswordResetRequestThrottle(PhoneRateThrottle):
    scope = "password_reset_request"
    setting_name = "PASSWORD_RESET_REQUEST_RATE"


class PasswordResetConfirmThrottle(PhoneRateThrottle):
    scope = "password_reset_confirm"
    setting_name = "PASSWORD_RESET_CONFIRM_RATE"
