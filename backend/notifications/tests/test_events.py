from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from catalog import services as catalog_services
from core.testing.factories import CustomerFactory, ProductFactory, StoreFactory
from notifications.models import Notification
from notifications.services import create_notification
from orders import services as order_services
from orders.models import Order
from orders.state_machine import Action
from orders.tests.helpers import place_order
from payments import services as payment_services
from payments.expiry import expire_unpaid_orders
from payments.providers.mock import build_webhook


@override_settings(MOCK_PAYMENT_WEBHOOK_SECRET="test-secret", MOBILE_MONEY_PROVIDER="mock")
class NotificationEventTests(TestCase):
    def setUp(self):
        self.customer = CustomerFactory()
        self.store = StoreFactory(delivery_fee=Decimal("2000.00"))
        self.owner_user = self.store.owner.user
        self.cola = ProductFactory(
            store=self.store, price=Decimal("1500.00"), stock_quantity=50, low_stock_threshold=5
        )

    def committed(self, func, *args, **kwargs):
        with self.captureOnCommitCallbacks(execute=True):
            return func(*args, **kwargs)

    def inbox(self, user):
        return list(
            Notification.objects.filter(user=user)
            .order_by("id")
            .values_list("notification_type", flat=True)
        )

    def assertInboxes(self, customer, owner):
        self.assertEqual(self.inbox(self.customer.user), customer)
        self.assertEqual(self.inbox(self.owner_user), owner)

    def order(self, method="CASH", quantity=1):
        return self.committed(
            place_order, self.customer, (self.cola, quantity), payment_method=method
        )

    def pay(self, order, *, succeeded=True):
        payment, _ = payment_services.initiate_payment(order)
        body, headers = build_webhook(
            payment.transaction_reference, succeeded=succeeded, amount=order.total_amount
        )
        self.committed(payment_services.handle_webhook, "mock", body, headers)

    def transition(self, order, action, user, reason=None):
        return self.committed(order_services.transition_order, order, action, user, reason)

    def test_cash_order_tells_customer_and_store_at_once(self):
        order = self.order()

        self.assertInboxes(["ORDER_RECEIVED"], ["ORDER_RECEIVED"])
        owner_note = Notification.objects.get(user=self.owner_user)
        self.assertEqual(owner_note.order, order)
        self.assertIn(order.order_number, owner_note.message)

    def test_mobile_order_reaches_store_only_after_payment(self):
        order = self.order("MPESA")
        self.assertInboxes(["ORDER_RECEIVED"], [])

        self.pay(order)

        self.assertInboxes(["ORDER_RECEIVED", "PAYMENT_SUCCESS"], ["ORDER_RECEIVED"])

    def test_failed_payment_tells_customer_only(self):
        self.pay(self.order("MPESA"), succeeded=False)

        self.assertInboxes(["ORDER_RECEIVED", "PAYMENT_FAILED"], [])

    def test_payment_after_cancel_does_not_send_order_to_store(self):
        order = self.order("MPESA")
        payment, _ = payment_services.initiate_payment(order)
        self.transition(order, Action.CANCEL, self.customer.user)
        body, headers = build_webhook(payment.transaction_reference, amount=order.total_amount)

        self.committed(payment_services.handle_webhook, "mock", body, headers)

        self.assertInboxes(["ORDER_RECEIVED", "ORDER_CANCELLED", "PAYMENT_SUCCESS"], [])

    def test_every_status_change_tells_the_customer(self):
        order = self.order()
        for action in (Action.ACCEPT, Action.PREPARE, Action.READY, Action.COMPLETE):
            self.transition(order, action, self.owner_user)

        self.assertInboxes(
            [
                "ORDER_RECEIVED",
                "ORDER_ACCEPTED",
                "ORDER_PREPARING",
                "ORDER_READY",
                "ORDER_COMPLETED",
            ],
            ["ORDER_RECEIVED"],
        )

    def test_reject_reason_reaches_customer(self):
        order = self.order()

        self.transition(order, Action.REJECT, self.owner_user, "Out of crates")

        rejected = Notification.objects.get(
            user=self.customer.user, notification_type="ORDER_REJECTED"
        )
        self.assertIn("Out of crates", rejected.message)

    def test_customer_cancel_tells_store_owner(self):
        order = self.order()

        self.transition(order, Action.CANCEL, self.customer.user)

        self.assertInboxes(
            ["ORDER_RECEIVED", "ORDER_CANCELLED"], ["ORDER_RECEIVED", "ORDER_CANCELLED"]
        )

    def test_store_never_hears_about_unpaid_mobile_order_cancel(self):
        order = self.order("MPESA")

        self.transition(order, Action.CANCEL, self.customer.user)

        self.assertInboxes(["ORDER_RECEIVED", "ORDER_CANCELLED"], [])

    def test_owner_cancel_does_not_notify_the_owner(self):
        order = self.order()
        self.transition(order, Action.ACCEPT, self.owner_user)

        self.transition(order, Action.CANCEL, self.owner_user, "Delivery bike broke")

        self.assertInboxes(
            ["ORDER_RECEIVED", "ORDER_ACCEPTED", "ORDER_CANCELLED"], ["ORDER_RECEIVED"]
        )

    def test_expired_order_tells_customer(self):
        order = self.order("MPESA")
        Order.objects.filter(pk=order.pk).update(ordered_at=timezone.now() - timedelta(hours=1))

        self.committed(expire_unpaid_orders)

        self.assertInboxes(["ORDER_RECEIVED", "ORDER_CANCELLED"], [])
        cancelled = Notification.objects.get(
            user=self.customer.user, notification_type="ORDER_CANCELLED"
        )
        self.assertIn("not received", cancelled.message)

    def test_low_stock_fires_once_per_crossing(self):
        catalog_services.set_stock(self.cola, 8)

        def low_stock_count():
            return Notification.objects.filter(
                user=self.owner_user, notification_type="LOW_STOCK"
            ).count()

        self.order(quantity=2)  # 8 -> 6, still above 5
        self.assertEqual(low_stock_count(), 0)
        self.order(quantity=1)  # 6 -> 5, crosses
        self.assertEqual(low_stock_count(), 1)
        self.order(quantity=1)  # 5 -> 4, already low
        self.assertEqual(low_stock_count(), 1)

        catalog_services.set_stock(self.cola, 10)
        self.order(quantity=7)  # 10 -> 3, crosses again
        self.assertEqual(low_stock_count(), 2)
        latest = Notification.objects.filter(notification_type="LOW_STOCK").latest("id")
        self.assertIn("down to 3", latest.message)
        self.assertEqual(self.inbox(self.customer.user).count("LOW_STOCK"), 0)

    def test_rolled_back_change_sends_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    create_notification(self.customer.user.pk, "ORDER_RECEIVED", "t", "m")
                    raise RuntimeError
            except RuntimeError:
                pass

        self.assertEqual(Notification.objects.count(), 0)
