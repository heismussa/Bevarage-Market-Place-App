from django.db import IntegrityError, transaction
from django.test import TestCase

from core.testing.factories import AddressFactory, CustomerFactory


class AddressConstraintTests(TestCase):
    def test_only_one_default_address_per_customer(self):
        customer = CustomerFactory()
        AddressFactory(customer=customer, is_default=True)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AddressFactory(customer=customer, is_default=True)

        AddressFactory(customer=customer, is_default=False)
        self.assertEqual(customer.addresses.count(), 2)

    def test_each_customer_can_have_a_default(self):
        AddressFactory(is_default=True)
        AddressFactory(is_default=True)
