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
from catalog.models import ProductUnit
from orders.models import Order, OrderItem


class OrderConstraintTests(TestCase):
    def setUp(self):
        self.customer = create_customer()
        self.store = create_store(create_store_owner())
        self.product = create_product(self.store, create_category())
        self.order = Order.objects.create(
            order_number="BDM-TEST-0001",
            customer=self.customer,
            store=self.store,
            delivery_address="Plot 12, Dar es Salaam",
            delivery_phone="+255712000001",
            subtotal_amount=Decimal("1500.00"),
            delivery_fee=Decimal("0.00"),
            total_amount=Decimal("1500.00"),
        )

    def test_quantity_must_be_greater_than_zero(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderItem.objects.create(
                    order=self.order,
                    product=self.product,
                    product_name="Cola",
                    unit=ProductUnit.BOTTLE,
                    quantity=0,
                    unit_price=Decimal("1500.00"),
                    subtotal=Decimal("0.00"),
                )
