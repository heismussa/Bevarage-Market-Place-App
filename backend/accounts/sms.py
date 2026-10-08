"""Outgoing SMS. Only a console backend exists until an SMS provider is chosen."""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _console(phone, message):
    logger.warning("SMS to %s: %s", phone, message)


BACKENDS = {"console": _console}


def send_sms(phone, message):
    backend = BACKENDS.get(settings.SMS_BACKEND)
    if backend is None:
        raise ImproperlyConfigured(f"Unknown SMS_BACKEND {settings.SMS_BACKEND!r}.")
    backend(phone, message)
