from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import (
    AddressFactory,
    OrderFactory,
    OrderItemFactory,
    OrderStatusHistoryFactory,
    PaymentFactory,
    ProductFactory,
    StoreFactory,
)
from orders.models import Order, OrderStatus
from orders.tests.helpers import fill_cart, place_order

LIST_URL = "/api/v1/orders/"


def detail_url(order):
    return f"{LIST_URL}{order.pk}/"


def cancel_url(order):
    return f"{LIST_URL}{order.pk}/cancel/"


def admin_cancel_url(order):
    return f"/api/v1/admin/orders/{order.pk}/cancel/"


class PlaceOrderApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()
        self.store = StoreFactory(delivery_fee=Decimal("2000.00"))
        self.cola = ProductFactory(store=self.store, price=Decimal("1500.00"), stock_quantity=5)
        self.address = AddressFactory(customer=self.customer)

    def test_place_order(self):
        fill_cart(self.customer, (self.cola, 2))

        response = self.client.post(
            LIST_URL,
            {"address_id": self.address.pk, "payment_method": "CASH", "notes": "Gate 2"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["order_status"], "PENDING")
        self.assertEqual(response.data["total_amount"], "5000.00")
        self.assertEqual(response.data["items"][0]["quantity"], 2)
        self.assertEqual(response.data["status_history"][0]["status"], "PENDING")
        self.assertEqual(response.data["payment"]["payment_method"], "CASH")
        self.assertEqual(response.data["allowed_actions"], ["cancel"])

    def test_price_tampering_has_no_effect(self):
        fill_cart(self.customer, (self.cola, 2))

        response = self.client.post(
            LIST_URL,
            {
                "address_id": self.address.pk,
                "payment_method": "CASH",
                "total_amount": "1.00",
                "subtotal_amount": "1.00",
                "delivery_fee": "0.00",
                "order_status": "COMPLETED",
                "payment_status": "SUCCESS",
                "items": [{"product": self.cola.pk, "quantity": 2, "unit_price": "1.00"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get()
        self.assertEqual(order.subtotal_amount, Decimal("3000.00"))
        self.assertEqual(order.delivery_fee, Decimal("2000.00"))
        self.assertEqual(order.total_amount, Decimal("5000.00"))
        self.assertEqual(order.order_status, "PENDING")
        self.assertEqual(order.payment_status, "PENDING")
        self.assertEqual(order.items.get().unit_price, Decimal("1500.00"))

    def test_double_submit_fails_with_empty_cart(self):
        fill_cart(self.customer, (self.cola, 1))
        body = {"address_id": self.address.pk, "payment_method": "CASH"}

        self.client.post(LIST_URL, body, format="json")
        second = self.client.post(LIST_URL, body, format="json")

        self.assertError(second, status.HTTP_409_CONFLICT, ErrorCode.EMPTY_CART)
        self.assertEqual(Order.objects.count(), 1)

    def test_validation(self):
        fill_cart(self.customer, (self.cola, 1))
        cases = (
            ({"payment_method": "CASH"}, "address_id"),
            ({"address_id": self.address.pk, "payment_method": "CARD"}, "payment_method"),
            (
                {"address_id": self.address.pk, "payment_method": "MPESA", "payer_phone": "07"},
                "payer_phone",
            ),
            ({"address_id": AddressFactory().pk, "payment_method": "CASH"}, "address_id"),
        )
        for body, field in cases:
            with self.subTest(field=field, body=body):
                error = self.assertError(
                    self.client.post(LIST_URL, body, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn(field, error["details"])
        self.assertFalse(Order.objects.exists())

    def test_insufficient_stock_lists_problems(self):
        fill_cart(self.customer, (self.cola, 3))
        self.cola.stock_quantity = 2
        self.cola.save()

        error = self.assertError(
            self.client.post(
                LIST_URL, {"address_id": self.address.pk, "payment_method": "CASH"}, format="json"
            ),
            status.HTTP_409_CONFLICT,
            ErrorCode.INSUFFICIENT_STOCK,
        )

        self.assertEqual(error["details"]["problems"][0]["max_available"], 2)


class CustomerOrderReadApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()

    def make_order(self, **kwargs):
        order = OrderFactory(customer=self.customer, **kwargs)
        OrderItemFactory.create_batch(2, order=order)
        OrderStatusHistoryFactory(order=order, changed_by=self.customer.user)
        PaymentFactory(order=order)
        return order

    def test_list_is_own_newest_first_and_filterable(self):
        older = self.make_order()
        newer = self.make_order(order_status=OrderStatus.CANCELLED)
        OrderFactory()

        response = self.client.get(LIST_URL)
        filtered = self.client.get(f"{LIST_URL}?status=CANCELLED")

        self.assertEqual([row["id"] for row in response.data["results"]], [newer.pk, older.pk])
        self.assertEqual(response.data["results"][0]["item_count"], 2)
        self.assertEqual([row["id"] for row in filtered.data["results"]], [newer.pk])

    def test_list_query_count_is_constant(self):
        for _ in range(4):
            self.make_order()

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(LIST_URL)

        self.assertEqual(len(response.data["results"]), 4)
        self.assertEqual(len(queries), 3)

    def test_detail_query_count(self):
        order = self.make_order()

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(detail_url(order))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["status_history"][0]["changed_by_role"], "CUSTOMER")
        self.assertEqual(len(queries), 5)

    def test_cannot_read_or_cancel_another_customers_order(self):
        other = OrderFactory()

        self.assertError(
            self.client.get(detail_url(other)), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND
        )
        self.assertError(
            self.client.post(cancel_url(other), {}, format="json"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        other.refresh_from_db()
        self.assertEqual(other.order_status, OrderStatus.PENDING)

    def test_store_owner_admin_and_anonymous_cannot_use_customer_endpoints(self):
        owner_client, _ = self.store_owner_client()
        admin_client, _ = self.admin_client()

        for client in (owner_client, admin_client):
            self.assertError(
                client.get(LIST_URL), status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED
            )
        self.assertError(
            APIClient().get(LIST_URL), status.HTTP_401_UNAUTHORIZED, ErrorCode.NOT_AUTHENTICATED
        )


class CancelApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()
        self.store = StoreFactory()
        self.cola = ProductFactory(store=self.store, stock_quantity=5)

    def test_customer_cancels_pending_order(self):
        order = place_order(self.customer, (self.cola, 2))

        response = self.client.post(cancel_url(order), {"reason": "Ordered twice"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["order_status"], "CANCELLED")
        self.assertEqual(response.data["status_reason"], "Ordered twice")
        self.assertEqual(response.data["allowed_actions"], [])
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 5)

    def test_customer_cannot_cancel_after_acceptance(self):
        order = OrderFactory(customer=self.customer, order_status=OrderStatus.ACCEPTED)

        error = self.assertError(
            self.client.post(cancel_url(order), {}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_TRANSITION,
        )

        self.assertEqual(error["details"]["order_status"], "ACCEPTED")

    def test_admin_cancels_any_open_order_with_reason(self):
        admin_client, _ = self.admin_client()
        order = place_order(self.customer, (self.cola, 1))
        Order.objects.filter(pk=order.pk).update(order_status=OrderStatus.PREPARING)

        missing_reason = admin_client.post(admin_cancel_url(order), {}, format="json")
        response = admin_client.post(
            admin_cancel_url(order), {"reason": "Customer called support"}, format="json"
        )

        error = self.assertError(
            missing_reason, status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR
        )
        self.assertIn("reason", error["details"])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["order_status"], "CANCELLED")
        self.assertEqual(response.data["status_history"][-1]["changed_by_role"], "ADMIN")
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 5)

    def test_admin_cannot_cancel_completed_order(self):
        admin_client, _ = self.admin_client()
        order = OrderFactory(order_status=OrderStatus.COMPLETED)

        self.assertError(
            admin_client.post(admin_cancel_url(order), {"reason": "x"}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_TRANSITION,
        )

    def test_only_admins_use_admin_cancel(self):
        order = OrderFactory(customer=self.customer)
        owner_client, _ = self.store_owner_client()

        for client in (self.client, owner_client):
            self.assertError(
                client.post(admin_cancel_url(order), {"reason": "x"}, format="json"),
                status.HTTP_403_FORBIDDEN,
                ErrorCode.PERMISSION_DENIED,
            )
