from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from cart.models import Cart
from catalog.models import AvailabilityStatus
from core.errors import ApiError, ErrorCode
from core.testing.factories import (
    AddressFactory,
    CustomerFactory,
    OrderFactory,
    ProductFactory,
    StoreFactory,
)
from orders import events, services
from orders.models import OrderStatus
from orders.tests.helpers import fill_cart, place_order
from payments.choices import PaymentStatus
from stores.models import StoreStatus


def today_prefix():
    return f"BDM-{timezone.localdate():%Y%m%d}-"


class CreateOrderTests(TestCase):
    def setUp(self):
        self.customer = CustomerFactory()
        self.store = StoreFactory(delivery_fee=Decimal("2000.00"))
        self.cola = ProductFactory(store=self.store, price=Decimal("1500.00"), stock_quantity=10)
        self.juice = ProductFactory(store=self.store, price=Decimal("2350.50"), stock_quantity=2)
        self.address = AddressFactory(
            customer=self.customer,
            address_line="Plot 12, Haile Selassie Road",
            area="Msasani",
            city="Dar es Salaam",
            phone="+255712345678",
        )

    def assertApiError(self, code, func, *args, **kwargs):
        with self.assertRaises(ApiError) as caught:
            func(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_creates_order_with_snapshots_and_database_prices(self):
        fill_cart(self.customer, (self.cola, 3), (self.juice, 2))
        self.cola.price = Decimal("1600.00")
        self.cola.save()

        order = services.create_order(
            self.customer, self.address.pk, "MPESA", notes="Call when you arrive"
        )

        self.assertTrue(order.order_number.startswith(today_prefix()))
        self.assertEqual(order.store, self.store)
        self.assertEqual(
            order.delivery_address, "Plot 12, Haile Selassie Road, Msasani, Dar es Salaam"
        )
        self.assertEqual(order.delivery_phone, "+255712345678")
        self.assertEqual(order.delivery_latitude, self.address.latitude)
        self.assertEqual(order.subtotal_amount, Decimal("9501.00"))
        self.assertEqual(order.delivery_fee, Decimal("2000.00"))
        self.assertEqual(order.total_amount, Decimal("11501.00"))
        self.assertEqual(order.order_status, OrderStatus.PENDING)
        self.assertEqual(order.notes, "Call when you arrive")

        items = {item.product_id: item for item in order.items.all()}
        self.assertEqual(items[self.cola.pk].unit_price, Decimal("1600.00"))
        self.assertEqual(items[self.cola.pk].subtotal, Decimal("4800.00"))
        self.assertEqual(items[self.cola.pk].product_name, self.cola.name)
        self.assertEqual(items[self.juice.pk].subtotal, Decimal("4701.00"))

        history = list(order.status_history.values_list("from_status", "status", "changed_by"))
        self.assertEqual(history, [(None, OrderStatus.PENDING, self.customer.user.pk)])

        payment = order.payments.get()
        self.assertEqual(payment.amount, Decimal("11501.00"))
        self.assertEqual(payment.payment_method, "MPESA")
        self.assertEqual(payment.payment_status, PaymentStatus.PENDING)
        self.assertEqual(payment.payer_phone, self.customer.user.phone)

    def test_takes_stock_and_syncs_availability(self):
        place_order(self.customer, (self.cola, 3), (self.juice, 2), address=self.address)

        self.cola.refresh_from_db()
        self.juice.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 7)
        self.assertEqual(self.cola.availability_status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(self.juice.stock_quantity, 0)
        self.assertEqual(self.juice.availability_status, AvailabilityStatus.OUT_OF_STOCK)

    def test_empties_cart_so_double_submit_fails(self):
        place_order(self.customer, (self.cola, 1), address=self.address)

        cart = Cart.objects.get(customer=self.customer)
        self.assertIsNone(cart.store)
        self.assertFalse(cart.items.exists())
        self.assertApiError(
            ErrorCode.EMPTY_CART, services.create_order, self.customer, self.address.pk, "CASH"
        )

    def test_customer_without_cart_gets_empty_cart(self):
        self.assertApiError(
            ErrorCode.EMPTY_CART, services.create_order, self.customer, self.address.pk, "CASH"
        )

    def test_cash_has_no_payer_phone_and_explicit_phone_is_kept(self):
        cash = place_order(self.customer, (self.cola, 1), address=self.address)
        mpesa = place_order(
            self.customer,
            (self.cola, 1),
            payment_method="MPESA",
            address=self.address,
            payer_phone="+255799000111",
        )

        self.assertIsNone(cash.payments.get().payer_phone)
        self.assertEqual(mpesa.payments.get().payer_phone, "+255799000111")

    def test_store_closed_after_adding(self):
        fill_cart(self.customer, (self.cola, 1))
        self.store.status = StoreStatus.CLOSED
        self.store.save()

        self.assertApiError(
            ErrorCode.STORE_CLOSED, services.create_order, self.customer, self.address.pk, "CASH"
        )
        self.assertTrue(Cart.objects.get(customer=self.customer).items.exists())

    def test_address_must_belong_to_customer(self):
        fill_cart(self.customer, (self.cola, 1))
        other_address = AddressFactory()

        with self.assertRaises(ValidationError) as caught:
            services.create_order(self.customer, other_address.pk, "CASH")
        self.assertIn("address_id", caught.exception.detail)

    def test_reports_every_problem_and_changes_nothing(self):
        fill_cart(self.customer, (self.cola, 3), (self.juice, 2))
        self.cola.availability_status = AvailabilityStatus.UNAVAILABLE
        self.cola.save()
        self.juice.stock_quantity = 1
        self.juice.save()

        error = self.assertApiError(
            ErrorCode.PRODUCT_UNAVAILABLE,
            services.create_order,
            self.customer,
            self.address.pk,
            "CASH",
        )

        codes = {p["product_id"]: p["code"] for p in error.details["problems"]}
        self.assertEqual(
            codes,
            {self.cola.pk: "PRODUCT_UNAVAILABLE", self.juice.pk: "INSUFFICIENT_STOCK"},
        )
        self.juice.refresh_from_db()
        self.assertEqual(self.juice.stock_quantity, 1)
        self.assertFalse(self.customer.orders.exists())

    def test_deleted_product_blocks_checkout(self):
        fill_cart(self.customer, (self.cola, 1))
        self.cola.deleted_at = timezone.now()
        self.cola.save()

        self.assertApiError(
            ErrorCode.PRODUCT_UNAVAILABLE,
            services.create_order,
            self.customer,
            self.address.pk,
            "CASH",
        )

    def test_order_numbers_are_sequential_per_day(self):
        first = place_order(self.customer, (self.cola, 1), address=self.address)
        second = place_order(self.customer, (self.cola, 1), address=self.address)

        self.assertEqual(first.order_number, f"{today_prefix()}0001")
        self.assertEqual(second.order_number, f"{today_prefix()}0002")

    def test_order_number_keeps_counting_past_9999(self):
        OrderFactory(order_number=f"{today_prefix()}9999")

        order = place_order(self.customer, (self.cola, 1), address=self.address)
        self.assertEqual(order.order_number, f"{today_prefix()}10000")

        following = place_order(self.customer, (self.cola, 1), address=self.address)
        self.assertEqual(following.order_number, f"{today_prefix()}10001")

    def test_event_fires_after_commit(self):
        with mock.patch.object(events, "notify_order_event") as notify:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                order = place_order(self.customer, (self.cola, 1), address=self.address)
            notify.assert_not_called()
            for callback in callbacks:
                callback()

        notify.assert_called_once_with(order, events.ORDER_CREATED)
