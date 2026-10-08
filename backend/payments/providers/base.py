"""The contract every payment provider implements.

A provider never decides that a payment succeeded on its own. initiate() only starts a
payment; SUCCESS comes from a webhook that passes verify_webhook().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


class InvalidWebhookPayload(ValueError):
    """The webhook body is signed correctly but cannot be understood."""


@dataclass(frozen=True)
class InitiationResult:
    status: str
    transaction_reference: str | None
    instructions: str
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentEvent:
    transaction_reference: str
    succeeded: bool
    amount: Decimal
    currency: str
    payload: dict


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def initiate(self, payment):
        """Start collecting payment. Returns an InitiationResult. Must not mark SUCCESS."""

    @abstractmethod
    def verify_webhook(self, body, headers):
        """True only if body (raw bytes) was really sent by this provider."""

    @abstractmethod
    def parse_event(self, body):
        """Turn a verified webhook body into a PaymentEvent or raise InvalidWebhookPayload."""
