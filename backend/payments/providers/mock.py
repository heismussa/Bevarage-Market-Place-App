"""Sandbox mobile-money provider for development and tests.

It behaves like a real gateway: initiate() returns a reference and the result arrives
later as a signed webhook. Webhooks are signed with HMAC-SHA256 over the raw body using
MOCK_PAYMENT_WEBHOOK_SECRET and sent in the X-Mock-Signature header (hex).

Simulate the customer approving or declining the prompt with:
    python manage.py simulate_mobile_money <reference> [--fail] [--amount 5000.00]
"""

import hashlib
import hmac
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings

from payments.choices import PaymentStatus
from payments.providers.base import (
    InitiationResult,
    InvalidWebhookPayload,
    PaymentEvent,
    PaymentProvider,
)

SIGNATURE_HEADER = "X-Mock-Signature"
SUCCESS = "SUCCESS"
FAILED = "FAILED"


def _secret():
    return settings.MOCK_PAYMENT_WEBHOOK_SECRET.encode()


def sign(body):
    return hmac.new(_secret(), body, hashlib.sha256).hexdigest()


def build_webhook(reference, *, succeeded=True, amount, currency="TZS"):
    """Return (body bytes, headers) exactly as the sandbox gateway would send them."""
    body = json.dumps(
        {
            "reference": reference,
            "status": SUCCESS if succeeded else FAILED,
            "amount": str(amount),
            "currency": currency,
        },
        separators=(",", ":"),
    ).encode()
    return body, {SIGNATURE_HEADER: sign(body)}


class MockMobileMoneyProvider(PaymentProvider):
    name = "mock"

    def initiate(self, payment):
        return InitiationResult(
            status=PaymentStatus.PROCESSING,
            transaction_reference=f"MOCK-{uuid.uuid4().hex[:20].upper()}",
            instructions=(
                f"A payment prompt for {payment.amount} {payment.currency} was sent to "
                f"{payment.payer_phone}. Enter your PIN to approve."
            ),
        )

    def verify_webhook(self, body, headers):
        signature = headers.get(SIGNATURE_HEADER, "")
        if not settings.MOCK_PAYMENT_WEBHOOK_SECRET or not signature:
            return False
        return hmac.compare_digest(sign(body), signature)

    def parse_event(self, body):
        try:
            data = json.loads(body)
            reference = str(data["reference"])
            status = data["status"]
            amount = Decimal(str(data["amount"]))
            currency = str(data.get("currency", "TZS"))
        except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise InvalidWebhookPayload("Malformed webhook body.") from exc
        if status not in (SUCCESS, FAILED) or not reference:
            raise InvalidWebhookPayload("Unknown status or missing reference.")
        return PaymentEvent(
            transaction_reference=reference,
            succeeded=status == SUCCESS,
            amount=amount,
            currency=currency,
            payload=data,
        )
