from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.factories import (
    create_category,
    create_customer,
    create_product,
    create_store,
    create_store_owner,
)
from cart.models import Cart, CartItem


class CartConstraintTests(TestCase):
    def setUp(self):
        self.customer = create_customer()
        self.store = create_store(create_store_owner())
        self.product = create_product(self.store, create_category())
        self.cart = Cart.objects.create(customer=self.customer, store=self.store)

    def test_quantity_must_be_greater_than_zero(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=self.product,
                    quantity=0,
                    unit_price=Decimal("1500.00"),
                )

    def test_product_is_unique_on_a_cart(self):
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            unit_price=Decimal("1500.00"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=self.product,
                    quantity=2,
                    unit_price=Decimal("1500.00"),
                )
