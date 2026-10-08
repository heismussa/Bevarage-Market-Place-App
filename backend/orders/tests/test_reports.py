from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from core.testing.factories import OrderFactory, OrderItemFactory, ProductFactory, StoreFactory
from orders import reports
from orders.models import Order, OrderStatus

DAR = ZoneInfo("Africa/Dar_es_Salaam")


def at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), tzinfo=DAR)


def make_order(store, status, total, ordered_at, items=()):
    order = OrderFactory(store=store, order_status=status, total_amount=Decimal(total))
    Order.objects.filter(pk=order.pk).update(ordered_at=ordered_at)
    for product, quantity in items:
        OrderItemFactory(order=order, product=product, quantity=quantity)
    return order


class AnalyticsTests(TestCase):
    """Hand-built data with known answers."""

    def setUp(self):
        self.store = StoreFactory()
        self.cola = ProductFactory(store=self.store, name="Cola", price=Decimal("1500.00"))
        self.juice = ProductFactory(store=self.store, name="Juice", price=Decimal("1000.00"))
        d1, d2, d3 = (datetime(2026, 10, day).date() for day in (1, 2, 3))
        self.d1, self.d3 = d1, d3

        make_order(self.store, OrderStatus.COMPLETED, "5000.00", at(d1, 10), [(self.cola, 3)])
        make_order(
            self.store,
            OrderStatus.COMPLETED,
            "7500.50",
            at(d1, 23, 30),
            [(self.cola, 2), (self.juice, 5)],
        )
        # 01:30 in Dar es Salaam is still Oct 1 in UTC; it must count for Oct 2.
        make_order(self.store, OrderStatus.COMPLETED, "3000.00", at(d2, 1, 30), [(self.juice, 1)])
        make_order(self.store, OrderStatus.PENDING, "4000.00", at(d2, 12), [(self.cola, 10)])
        make_order(self.store, OrderStatus.CANCELLED, "9000.00", at(d3, 9), [(self.cola, 6)])
        make_order(self.store, OrderStatus.COMPLETED, "2000.00", at(d1 - timedelta(days=1), 12))
        make_order(StoreFactory(), OrderStatus.COMPLETED, "100000.00", at(d1, 12))

    def test_totals(self):
        data = reports.analytics(self.store, self.d1, self.d3)

        self.assertEqual(data["total_orders"], 5)
        self.assertEqual(data["completed_orders"], 3)
        self.assertEqual(data["pending_orders"], 1)
        self.assertEqual(data["total_sales"], Decimal("15500.50"))

    def test_daily_series_uses_local_days_and_fills_gaps(self):
        data = reports.analytics(self.store, self.d1, self.d3)

        self.assertEqual(
            [(row["date"].day, row["orders"], row["sales"]) for row in data["daily_sales"]],
            [
                (1, 2, Decimal("12500.50")),
                (2, 1, Decimal("3000.00")),
                (3, 0, Decimal("0.00")),
            ],
        )

    def test_top_products_count_completed_orders_only(self):
        data = reports.analytics(self.store, self.d1, self.d3)

        self.assertEqual(
            [
                (row["product_name"], row["quantity_sold"], row["sales"])
                for row in data["top_products"]
            ],
            [("Juice", 6, Decimal("6000.00")), ("Cola", 5, Decimal("7500.00"))],
        )

    def test_empty_range(self):
        day = datetime(2026, 1, 1).date()

        data = reports.analytics(self.store, day, day)

        self.assertEqual(data["total_orders"], 0)
        self.assertEqual(data["total_sales"], Decimal("0.00"))
        self.assertEqual(data["top_products"], [])
        self.assertEqual(len(data["daily_sales"]), 1)


class DashboardTests(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.today = timezone.localdate()

    def test_numbers(self):
        make_order(self.store, OrderStatus.COMPLETED, "5000.00", at(self.today, 0, 5))
        make_order(self.store, OrderStatus.COMPLETED, "2500.00", at(self.today - timedelta(6), 9))
        make_order(self.store, OrderStatus.COMPLETED, "1000.00", at(self.today - timedelta(7), 9))
        make_order(self.store, OrderStatus.PENDING, "4000.00", at(self.today, 0, 1))
        make_order(self.store, OrderStatus.REJECTED, "3000.00", at(self.today, 0, 2))
        make_order(StoreFactory(), OrderStatus.PENDING, "9999.00", at(self.today, 0, 3))

        data = reports.dashboard(self.store)

        self.assertEqual(data["total_orders"], 5)
        self.assertEqual(data["pending_orders"], 1)
        self.assertEqual(data["total_sales"], Decimal("8500.00"))
        series = data["sales_last_7_days"]
        self.assertEqual(len(series), 7)
        self.assertEqual(series[0]["date"], self.today - timedelta(6))
        self.assertEqual(series[0]["sales"], Decimal("2500.00"))
        self.assertEqual(series[-1]["date"], self.today)
        self.assertEqual(series[-1]["sales"], Decimal("5000.00"))
        self.assertEqual(sum(row["orders"] for row in series), 2)

    def test_low_stock_items(self):
        ProductFactory(store=self.store, name="At threshold", stock_quantity=5)
        ProductFactory(store=self.store, name="Below", stock_quantity=2)
        ProductFactory(store=self.store, name="Fine", stock_quantity=6)
        ProductFactory(
            store=self.store, name="Deleted", stock_quantity=0, deleted_at=timezone.now()
        )
        ProductFactory(name="Other store", stock_quantity=0)

        data = reports.dashboard(self.store)

        self.assertEqual(data["low_stock_count"], 2)
        self.assertEqual([p.name for p in data["low_stock_items"]], ["Below", "At threshold"])

    def test_recent_orders_are_newest_five(self):
        orders = [
            make_order(self.store, OrderStatus.PENDING, "1000.00", at(self.today, 0, minute))
            for minute in range(7)
        ]

        data = reports.dashboard(self.store)

        self.assertEqual(
            [order.pk for order in data["recent_orders"]],
            [order.pk for order in reversed(orders[2:])],
        )
