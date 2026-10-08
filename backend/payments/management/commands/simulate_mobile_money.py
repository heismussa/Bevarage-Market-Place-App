from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from payments.models import Payment
from payments.providers.mock import build_webhook
from payments.services import handle_webhook


class Command(BaseCommand):
    help = (
        "Sandbox only: act as the mock mobile-money gateway and deliver a signed webhook "
        "for a payment reference, as if the customer approved or declined the prompt."
    )

    def add_arguments(self, parser):
        parser.add_argument("reference", help="transaction_reference, e.g. MOCK-3F9A...")
        parser.add_argument("--fail", action="store_true", help="Simulate a declined prompt.")
        parser.add_argument(
            "--amount", type=Decimal, help="Paid amount. Defaults to the payment amount."
        )

    def handle(self, *args, reference, fail, amount, **options):
        payment = Payment.objects.filter(transaction_reference=reference).first()
        if payment is None:
            raise CommandError(f"No payment with reference {reference}.")
        body, headers = build_webhook(
            reference,
            succeeded=not fail,
            amount=amount if amount is not None else payment.amount,
            currency=payment.currency,
        )
        try:
            payment = handle_webhook("mock", body, headers)
        except Exception as exc:
            raise CommandError(f"Webhook rejected: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(f"Payment {reference} is now {payment.payment_status}.")
        )
