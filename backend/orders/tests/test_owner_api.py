from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status

from core.errors import ErrorCode
from core.testing.api import ApiTestCase, authenticated_client
from core.testing.factories import (
    CustomerFactory,
    OrderFactory,
    OrderItemFactory,
    PaymentFactory,
    ProductFactory,
    StoreFactory,
)
from orders.models import Order, OrderStatus
from orders.tests.helpers import place_order

DAR = ZoneInfo("Africa/Dar_es_Salaam")


def store_orders_url(store):
    return f"/api/v1/owner/stores/{store.pk}/orders/"


def order_url(order):
    return f"/api/v1/owner/orders/{order.pk}/"


def transition_url(order):
    return f"/api/v1/owner/orders/{order.pk}/transition/"


def dashboard_url(store):
    return f"/api/v1/owner/stores/{store.pk}/dashboard/"


def analytics_url(store):
    return f"/api/v1/owner/stores/{store.pk}/analytics/"


def ids(response):
    return [row["id"] for row in response.data["results"]]


class OwnerOrderListTests(ApiTestCase):
    def setUp(self):
        self.client, self.owner = self.store_owner_client()
        self.store = StoreFactory(owner=self.owner)

    def make(self, day, name="Asha Juma", **kwargs):
        customer = CustomerFactory(user__full_name=name)
        order = OrderFactory(store=self.store, customer=customer, **kwargs)
        Order.objects.filter(pk=order.pk).update(
            ordered_at=datetime.combine(day, time(12), tzinfo=DAR)
        )
        OrderItemFactory(order=order)
        PaymentFactory(order=order, payment_method="MPESA")
        return order

    def test_list_filters_and_search(self):
        d1, d2, d3 = (datetime(2026, 10, day).date() for day in (1, 2, 3))
        first = self.make(d1, name="Asha Juma")
        second = self.make(d2, name="Baraka Mushi", order_status=OrderStatus.ACCEPTED)
        third = self.make(d3, name="Neema Said", order_number="BDM-20261003-0042")
        OrderFactory()

        cases = (
            ("", [third.pk, second.pk, first.pk]),
            ("?status=ACCEPTED", [second.pk]),
            ("?date_from=2026-10-02", [third.pk, second.pk]),
            ("?date_from=2026-10-01&date_to=2026-10-02", [second.pk, first.pk]),
            ("?search=baraka", [second.pk]),
            ("?search=0042", [third.pk]),
            ("?ordering=ordered_at", [first.pk, second.pk, third.pk]),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(
                    ids(self.client.get(store_orders_url(self.store) + query)), expected
                )

    def test_list_row_shape(self):
        self.make(timezone.localdate(), name="Asha Juma")

        row = self.client.get(store_orders_url(self.store)).data["results"][0]

        self.assertEqual(row["customer"]["full_name"], "Asha Juma")
        self.assertEqual(row["payment_method"], "MPESA")
        self.assertEqual(row["item_count"], 1)

    def test_invalid_date_range(self):
        error = self.assertError(
            self.client.get(
                store_orders_url(self.store) + "?date_from=2026-10-05&date_to=2026-10-01"
            ),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("date_to", error["details"])

    def test_query_count_is_constant(self):
        for _ in range(5):
            self.make(timezone.localdate())

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(store_orders_url(self.store))

        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(len(queries), 4)

    def test_other_owners_store_is_not_found(self):
        other_store = StoreFactory()
        OrderFactory(store=other_store)

        for url in (
            store_orders_url(other_store),
            dashboard_url(other_store),
            analytics_url(other_store),
        ):
            with self.subTest(url=url):
                self.assertError(
                    self.client.get(url), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND
                )

    def test_customers_are_rejected(self):
        customer_client, _ = self.customer_client()

        for url in (
            store_orders_url(self.store),
            dashboard_url(self.store),
            analytics_url(self.store),
        ):
            with self.subTest(url=url):
                self.assertError(
                    customer_client.get(url), status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED
                )


class OwnerOrderDetailAndTransitionTests(ApiTestCase):
    def setUp(self):
        self.client, self.owner = self.store_owner_client()
        self.store = StoreFactory(owner=self.owner)
        self.cola = ProductFactory(store=self.store, stock_quantity=5, price=Decimal("1500.00"))
        self.customer = CustomerFactory(user__full_name="Asha Juma")
        self.order = place_order(self.customer, (self.cola, 2))

    def test_detail_shows_customer_and_owner_actions(self):
        response = self.client.get(order_url(self.order))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["customer"]["full_name"], "Asha Juma")
        self.assertEqual(response.data["customer"]["phone"], self.customer.user.phone)
        self.assertEqual(response.data["delivery_phone"], self.order.delivery_phone)
        self.assertEqual(response.data["allowed_actions"], ["accept", "reject"])
        self.assertEqual(response.data["payment_status"], "PENDING")
        self.assertEqual(len(response.data["status_history"]), 1)

    def test_full_happy_path(self):
        for action, expected in (
            ("accept", "ACCEPTED"),
            ("prepare", "PREPARING"),
            ("ready", "READY"),
            ("complete", "COMPLETED"),
        ):
            with self.subTest(action=action):
                response = self.client.post(
                    transition_url(self.order), {"action": action}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertEqual(response.data["order_status"], expected)
        self.assertEqual(response.data["allowed_actions"], [])

    def test_reject_requires_reason_and_restores_stock(self):
        missing = self.client.post(transition_url(self.order), {"action": "reject"}, format="json")
        error = self.assertError(missing, status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR)
        self.assertIn("reason", error["details"])

        response = self.client.post(
            transition_url(self.order), {"action": "reject", "reason": "No crates"}, format="json"
        )

        self.assertEqual(response.data["order_status"], "REJECTED")
        self.assertEqual(response.data["status_reason"], "No crates")
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 5)

    def test_cancel_after_accept_requires_reason(self):
        self.client.post(transition_url(self.order), {"action": "accept"}, format="json")

        self.assertError(
            self.client.post(transition_url(self.order), {"action": "cancel"}, format="json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        response = self.client.post(
            transition_url(self.order),
            {"action": "cancel", "reason": "Crate broke"},
            format="json",
        )
        self.assertEqual(response.data["order_status"], "CANCELLED")

    def test_invalid_transition(self):
        error = self.assertError(
            self.client.post(transition_url(self.order), {"action": "complete"}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.INVALID_TRANSITION,
        )
        self.assertEqual(error["details"]["allowed_actions"], ["accept", "reject"])

    def test_unknown_action_is_validation_error(self):
        self.assertError(
            self.client.post(transition_url(self.order), {"action": "deliver"}, format="json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )

    def test_other_owner_cannot_see_or_transition(self):
        other_client, _ = self.store_owner_client()

        self.assertError(
            other_client.get(order_url(self.order)), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND
        )
        self.assertError(
            other_client.post(transition_url(self.order), {"action": "accept"}, format="json"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_customer_cannot_use_owner_transition(self):
        customer_client = authenticated_client(self.customer.user)

        self.assertError(
            customer_client.post(transition_url(self.order), {"action": "accept"}, format="json"),
            status.HTTP_403_FORBIDDEN,
            ErrorCode.PERMISSION_DENIED,
        )


class DashboardAndAnalyticsApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.owner = self.store_owner_client()
        self.store = StoreFactory(owner=self.owner)
        self.today = timezone.localdate()
        cola = ProductFactory(store=self.store, name="Cola", stock_quantity=3)
        for minute in range(3):
            order = OrderFactory(
                store=self.store,
                order_status=OrderStatus.COMPLETED,
                total_amount=Decimal("5000.00"),
            )
            Order.objects.filter(pk=order.pk).update(
                ordered_at=datetime.combine(self.today, time(0, minute), tzinfo=DAR)
            )
            OrderItemFactory(order=order, product=cola, quantity=2)

    def test_dashboard(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(dashboard_url(self.store))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_orders"], 3)
        self.assertEqual(response.data["total_sales"], "15000.00")
        self.assertEqual(response.data["low_stock_count"], 1)
        self.assertEqual(response.data["low_stock_items"][0]["name"], "Cola")
        self.assertEqual(response.data["sales_last_7_days"][-1]["sales"], "15000.00")
        self.assertEqual(len(response.data["recent_orders"]), 3)
        self.assertEqual(len(queries), 7)

    def test_analytics_defaults_to_last_30_days(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(analytics_url(self.store))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date_to"], self.today.isoformat())
        self.assertEqual(response.data["date_from"], (self.today - timedelta(days=29)).isoformat())
        self.assertEqual(len(response.data["daily_sales"]), 30)
        self.assertEqual(response.data["completed_orders"], 3)
        self.assertEqual(response.data["top_products"][0]["quantity_sold"], 6)
        self.assertEqual(len(queries), 5)

    def test_analytics_explicit_range(self):
        query = f"?from={self.today.isoformat()}&to={self.today.isoformat()}"

        response = self.client.get(analytics_url(self.store) + query)

        self.assertEqual(response.data["total_sales"], "15000.00")
        self.assertEqual(len(response.data["daily_sales"]), 1)

    def test_analytics_validation(self):
        cases = (
            ("?from=2026-10-05&to=2026-10-01", "to"),
            ("?from=2025-01-01&to=2026-10-01", "from"),
            ("?from=yesterday", "from"),
        )
        for query, field in cases:
            with self.subTest(query=query):
                error = self.assertError(
                    self.client.get(analytics_url(self.store) + query),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn(field, error["details"])
