from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import (
    create_category,
    create_product,
    create_store,
    create_store_owner,
)


class ProductConstraintTests(TestCase):
    def setUp(self):
        self.store = create_store(create_store_owner())
        self.category = create_category()

    def test_price_must_be_greater_than_zero(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_product(self.store, self.category, name="Free", price=Decimal("0.00"))

    def test_stock_cannot_be_negative(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_product(self.store, self.category, name="Missing", stock=-1)

    def test_low_stock_threshold_cannot_be_negative(self):
        product = create_product(self.store, self.category, name="Cola")
        product.low_stock_threshold = -1
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                product.save(update_fields=["low_stock_threshold"])

    def test_active_product_name_is_unique_per_store(self):
        create_product(self.store, self.category, name="Cola")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_product(self.store, self.category, name="Cola")

    def test_soft_deleted_product_frees_the_name(self):
        first = create_product(self.store, self.category, name="Cola")
        first.deleted_at = timezone.now()
        first.save(update_fields=["deleted_at"])

        second = create_product(self.store, self.category, name="Cola")
        self.assertNotEqual(first.pk, second.pk)
