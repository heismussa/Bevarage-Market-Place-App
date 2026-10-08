from decimal import Decimal

from payments.models import Payment
from payments.providers.mock import build_webhook

WEBHOOK_URL = "/api/v1/payments/webhook/mock/"


def send_webhook(client, reference, *, succeeded=True, amount, currency="TZS", headers=None):
    body, signed_headers = build_webhook(
        reference, succeeded=succeeded, amount=Decimal(amount), currency=currency
    )
    return client.post(
        WEBHOOK_URL,
        data=body,
        content_type="application/json",
        headers=signed_headers if headers is None else headers,
    )


def latest(order):
    return Payment.objects.filter(order=order).order_by("-created_at", "-id").first()
