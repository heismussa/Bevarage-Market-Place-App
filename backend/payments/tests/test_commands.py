from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from core.testing.factories import CustomerFactory, ProductFactory, StoreFactory
from orders.models import Order, OrderStatus
from orders.tests.helpers import place_order
from payments import services
from payments.choices import PaymentStatus


def age(order, minutes):
    Order.objects.filter(pk=order.pk).update(ordered_at=timezone.now() - timedelta(minutes=minutes))


@override_settings(
    PAYMENT_TIMEOUT_MINUTES=15,
    MOCK_PAYMENT_WEBHOOK_SECRET="test-secret",
    MOBILE_MONEY_PROVIDER="mock",
)
class ExpireUnpaidOrdersTests(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.cola = ProductFactory(store=self.store, stock_quantity=10, price=Decimal("1500.00"))

    def order(self, method, minutes_old, quantity=1):
        order = place_order(CustomerFactory(), (self.cola, quantity), payment_method=method)
        age(order, minutes_old)
        return order

    def run_command(self):
        out = StringIO()
        call_command("expire_unpaid_orders", stdout=out)
        return out.getvalue()

    def test_cancels_only_old_unpaid_mobile_orders(self):
        expired = self.order("MPESA", 20, quantity=3)
        processing = self.order("TIGO_PESA", 30)
        services.initiate_payment(processing)
        fresh = self.order("MPESA", 5)
        cash = self.order("CASH", 60)
        paid = self.order("AIRTEL_MONEY", 60)
        Order.objects.filter(pk=paid.pk).update(payment_status=PaymentStatus.SUCCESS)
        accepted = self.order("MPESA", 60)
        Order.objects.filter(pk=accepted.pk).update(order_status=OrderStatus.ACCEPTED)

        output = self.run_command()

        self.assertIn("Expired 2 unpaid order(s)", output)
        statuses = {
            order.pk: Order.objects.get(pk=order.pk).order_status
            for order in (expired, processing, fresh, cash, paid, accepted)
        }
        self.assertEqual(
            statuses,
            {
                expired.pk: OrderStatus.CANCELLED,
                processing.pk: OrderStatus.CANCELLED,
                fresh.pk: OrderStatus.PENDING,
                cash.pk: OrderStatus.PENDING,
                paid.pk: OrderStatus.PENDING,
                accepted.pk: OrderStatus.ACCEPTED,
            },
        )
        entry = expired.status_history.order_by("-id").first()
        self.assertIsNone(entry.changed_by)
        self.assertIn("15 minutes", entry.notes)

    def test_restores_stock_and_is_safe_to_rerun(self):
        self.order("MPESA", 20, quantity=4)
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 6)

        self.run_command()
        second = self.run_command()

        self.assertIn("Expired 0 unpaid order(s)", second)
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 10)


@override_settings(MOCK_PAYMENT_WEBHOOK_SECRET="test-secret", MOBILE_MONEY_PROVIDER="mock")
class SimulateMobileMoneyTests(TestCase):
    def test_simulates_approval(self):
        order = place_order(CustomerFactory(), (ProductFactory(), 1), payment_method="MPESA")
        payment, _ = services.initiate_payment(order)
        out = StringIO()

        call_command("simulate_mobile_money", payment.transaction_reference, stdout=out)

        self.assertIn("SUCCESS", out.getvalue())
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.SUCCESS)
