from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from core.testing.factories import ProductFactory, StoreFactory


class ProductConstraintTests(TestCase):
    def setUp(self):
        self.store = StoreFactory()

    def test_price_must_be_greater_than_zero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductFactory(store=self.store, price=Decimal("0.00"))

    def test_stock_cannot_be_negative(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductFactory(store=self.store, stock_quantity=-1)

    def test_low_stock_threshold_cannot_be_negative(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductFactory(store=self.store, low_stock_threshold=-1)

    def test_active_product_name_is_unique_per_store(self):
        ProductFactory(store=self.store, name="Cola")

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductFactory(store=self.store, name="Cola")

    def test_same_name_is_allowed_in_another_store(self):
        ProductFactory(store=self.store, name="Cola")
        ProductFactory(name="Cola")

    def test_soft_deleted_product_frees_the_name(self):
        first = ProductFactory(store=self.store, name="Cola", deleted_at=timezone.now())

        second = ProductFactory(store=self.store, name="Cola")

        self.assertNotEqual(first.pk, second.pk)
