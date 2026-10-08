from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.tokens import ensure_current


class SessionJWTAuthentication(JWTAuthentication):
    """JWT authentication that also rejects tokens from before a password change."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        ensure_current(user, validated_token)
        return user
