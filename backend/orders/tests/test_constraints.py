from django.db import IntegrityError, transaction
from django.test import TestCase

from core.testing.factories import OrderFactory, OrderItemFactory


class OrderConstraintTests(TestCase):
    def test_quantity_must_be_greater_than_zero(self):
        order = OrderFactory()

        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItemFactory(order=order, quantity=0)
