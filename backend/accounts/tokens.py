"""JWTs tied to the user's current password.

Every token carries a short fingerprint of the password hash. Changing or resetting
the password changes the fingerprint, so every token issued before stops working.
"""

from django.contrib.auth import get_user_model
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

PASSWORD_CLAIM = "pwd"


def password_fingerprint(user):
    return salted_hmac("accounts.tokens.password", user.password).hexdigest()[:16]


class SessionRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token[PASSWORD_CLAIM] = password_fingerprint(user)
        return token


def ensure_current(user, token):
    """Raise InvalidToken if the token was issued before the last password change."""
    claim = token.get(PASSWORD_CLAIM)
    if not claim or not constant_time_compare(claim, password_fingerprint(user)):
        raise InvalidToken("Token is no longer valid. Log in again.")


def user_for_token(token):
    user_id = token.get(api_settings.USER_ID_CLAIM)
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise InvalidToken("Token is no longer valid. Log in again.")
    return user
