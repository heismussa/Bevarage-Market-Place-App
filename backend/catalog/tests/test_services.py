from decimal import Decimal

from django.test import TestCase

from catalog import services
from catalog.models import AvailabilityStatus, Product, ProductUnit
from core.testing.factories import CategoryFactory, ProductFactory, StoreFactory

AVAILABLE = AvailabilityStatus.AVAILABLE
OUT_OF_STOCK = AvailabilityStatus.OUT_OF_STOCK
UNAVAILABLE = AvailabilityStatus.UNAVAILABLE


class ComputeAvailabilityTests(TestCase):
    def test_rules(self):
        cases = (
            (AVAILABLE, 0, OUT_OF_STOCK),
            (AVAILABLE, 5, AVAILABLE),
            (OUT_OF_STOCK, 0, OUT_OF_STOCK),
            (OUT_OF_STOCK, 1, AVAILABLE),
            (UNAVAILABLE, 3, UNAVAILABLE),
            (UNAVAILABLE, 0, UNAVAILABLE),
        )
        for current, stock, expected in cases:
            with self.subTest(current=current, stock=stock):
                self.assertEqual(services.compute_availability(current, stock), expected)


class SyncAvailabilityTests(TestCase):
    def test_bulk_update_matches_compute_availability(self):
        rows = {
            "drained": ProductFactory(availability_status=AVAILABLE),
            "restocked": ProductFactory(availability_status=AVAILABLE),
            "hidden": ProductFactory(availability_status=UNAVAILABLE),
            "hidden_drained": ProductFactory(availability_status=UNAVAILABLE),
        }
        Product.objects.filter(pk__in=[rows["drained"].pk, rows["hidden_drained"].pk]).update(
            stock_quantity=0
        )
        Product.objects.filter(pk=rows["restocked"].pk).update(
            availability_status=OUT_OF_STOCK, stock_quantity=7
        )

        services.sync_availability(Product.objects.all())

        statuses = {
            key: Product.objects.get(pk=product.pk).availability_status
            for key, product in rows.items()
        }
        self.assertEqual(
            statuses,
            {
                "drained": OUT_OF_STOCK,
                "restocked": AVAILABLE,
                "hidden": UNAVAILABLE,
                "hidden_drained": UNAVAILABLE,
            },
        )


class StockServiceTests(TestCase):
    def test_set_stock_to_zero_and_back(self):
        product = ProductFactory(stock_quantity=10)

        product = services.set_stock(product, 0)
        self.assertEqual(product.availability_status, OUT_OF_STOCK)

        product = services.set_stock(product, 12)
        self.assertEqual(product.availability_status, AVAILABLE)
        self.assertEqual(Product.objects.get(pk=product.pk).stock_quantity, 12)

    def test_create_with_zero_stock_is_out_of_stock(self):
        product = services.create_product(
            StoreFactory(),
            {
                "category": CategoryFactory(),
                "name": "Zero stock",
                "unit": ProductUnit.CAN,
                "price": Decimal("1000.00"),
                "stock_quantity": 0,
            },
        )

        self.assertEqual(product.availability_status, OUT_OF_STOCK)

    def test_soft_delete_sets_deleted_at_once(self):
        product = ProductFactory()

        first = services.soft_delete_product(product)
        second = services.soft_delete_product(product)

        self.assertIsNotNone(first.deleted_at)
        self.assertEqual(first.deleted_at, second.deleted_at)
