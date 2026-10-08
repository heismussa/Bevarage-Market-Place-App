from payments.choices import PaymentStatus
from payments.providers.base import InitiationResult, InvalidWebhookPayload, PaymentProvider


class CashProvider(PaymentProvider):
    """Cash on delivery. The payment becomes SUCCESS when the store completes the order."""

    name = "cash"

    def initiate(self, payment):
        return InitiationResult(
            status=PaymentStatus.PENDING,
            transaction_reference=None,
            instructions="Pay the driver in cash when your order arrives.",
        )

    def verify_webhook(self, body, headers):
        return False

    def parse_event(self, body):
        raise InvalidWebhookPayload("Cash payments have no webhooks.")
