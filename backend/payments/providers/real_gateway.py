"""SKELETON ONLY. Not registered and never used until it is implemented.

Copy this class when integrating a real mobile-money or card gateway. Keep every
credential in environment variables and read them through django.conf.settings.
"""

from payments.providers.base import PaymentProvider


class RealGatewayProvider(PaymentProvider):
    name = "real_gateway"

    def initiate(self, payment):
        # TODO: call the gateway's "request payment" API with payment.amount,
        # payment.currency and payment.payer_phone.
        # TODO: return InitiationResult(status=PROCESSING, transaction_reference=<gateway id>,
        # instructions=<text for the customer>).
        raise NotImplementedError("RealGatewayProvider is a skeleton.")

    def verify_webhook(self, body, headers):
        # TODO: verify the gateway's signature (or IP allow-list) using a secret from the
        # environment. Use hmac.compare_digest for any comparison.
        raise NotImplementedError("RealGatewayProvider is a skeleton.")

    def parse_event(self, body):
        # TODO: map the gateway payload to PaymentEvent. Raise InvalidWebhookPayload for
        # bodies that cannot be understood.
        raise NotImplementedError("RealGatewayProvider is a skeleton.")
