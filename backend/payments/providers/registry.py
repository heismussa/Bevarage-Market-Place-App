from django.conf import settings

from payments.choices import MOBILE_MONEY_METHODS, PaymentMethod
from payments.providers.cash import CashProvider
from payments.providers.mock import MockMobileMoneyProvider

# Provider name -> instance. The name is also the webhook URL segment.
PROVIDERS = {provider.name: provider for provider in (CashProvider(), MockMobileMoneyProvider())}


def get_provider(name):
    """Provider by name, or None."""
    return PROVIDERS.get(name)


def provider_for_method(payment_method):
    """Provider that handles a payment method, or None if no provider is configured."""
    if payment_method == PaymentMethod.CASH:
        return PROVIDERS["cash"]
    if payment_method in MOBILE_MONEY_METHODS:
        return PROVIDERS.get(settings.MOBILE_MONEY_PROVIDER)
    return None
