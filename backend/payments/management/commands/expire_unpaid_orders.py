from django.conf import settings
from django.core.management.base import BaseCommand

from payments.expiry import expire_unpaid_orders


class Command(BaseCommand):
    help = (
        "Cancel PENDING mobile-money orders that are still unpaid after "
        "PAYMENT_TIMEOUT_MINUTES and return their stock. Safe to run repeatedly (cron)."
    )

    def handle(self, *args, **options):
        count = expire_unpaid_orders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {count} unpaid order(s) older than "
                f"{settings.PAYMENT_TIMEOUT_MINUTES} minutes."
            )
        )
