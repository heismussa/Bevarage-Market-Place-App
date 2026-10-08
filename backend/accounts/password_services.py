"""Forgot-password and change-password rules.

Reset codes are 6 digits derived from the user's current password hash and a time
window, so nothing is stored: a code expires with its window and dies as soon as the
password changes. Wrong guesses are limited by throttles on the endpoints.
"""

import time

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import ValidationError

from accounts.models import User
from accounts.sms import send_sms

INVALID_CODE = "The code is wrong or has expired. Request a new one."


def _window_seconds():
    return settings.PASSWORD_RESET_CODE_MINUTES * 60


def reset_code(user, window=None):
    if window is None:
        window = int(time.time() // _window_seconds())
    digest = salted_hmac(
        "accounts.password_reset", f"{user.pk}:{user.password}:{window}"
    ).hexdigest()
    return f"{int(digest, 16) % 1_000_000:06d}"


def _code_is_valid(user, code):
    current = int(time.time() // _window_seconds())
    # The previous window too, so a code sent just before a boundary still works.
    return any(
        constant_time_compare(code, reset_code(user, window)) for window in (current, current - 1)
    )


def _active_user(phone):
    return User.objects.filter(phone=phone, is_active=True).first()


def _validated_password(password, user):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": list(exc.messages)}) from exc
    return password


def request_password_reset(phone):
    """Send a reset code if the phone belongs to an active user. Silent otherwise,
    so the response never reveals which numbers are registered."""
    user = _active_user(phone)
    if user is None:
        return
    minutes = settings.PASSWORD_RESET_CODE_MINUTES
    send_sms(
        user.phone,
        f"Your BeverageMart reset code is {reset_code(user)}. "
        f"It expires in {minutes} minutes. Do not share it.",
    )


@transaction.atomic
def confirm_password_reset(phone, code, new_password):
    user = _active_user(phone)
    if user is None or not _code_is_valid(user, code):
        raise ValidationError({"code": [INVALID_CODE]})
    user.set_password(_validated_password(new_password, user))
    user.save(update_fields=["password", "updated_at"])
    return user


@transaction.atomic
def change_password(user, current_password, new_password):
    if not user.check_password(current_password):
        raise ValidationError({"current_password": ["The current password is wrong."]})
    user.set_password(_validated_password(new_password, user))
    user.save(update_fields=["password", "updated_at"])
    return user
