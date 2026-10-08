from django.db import IntegrityError, transaction
from django.test import TestCase

from core.testing.factories import CartFactory, CartItemFactory, ProductFactory


class CartConstraintTests(TestCase):
    def setUp(self):
        self.product = ProductFactory()
        self.cart = CartFactory(store=self.product.store)

    def test_quantity_must_be_greater_than_zero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItemFactory(cart=self.cart, product=self.product, quantity=0)

    def test_product_is_unique_on_a_cart(self):
        CartItemFactory(cart=self.cart, product=self.product)

        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItemFactory(cart=self.cart, product=self.product, quantity=2)
