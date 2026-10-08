from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class PaymentInitiationThrottle(UserRateThrottle):
    """Limits payment attempts per customer. Rate comes from PAYMENT_INITIATION_RATE."""

    scope = "payment_initiation"

    def get_rate(self):
        return settings.PAYMENT_INITIATION_RATE
