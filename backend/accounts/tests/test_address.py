from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Address
from accounts.tests.factories import create_customer


class AddressConstraintTests(TestCase):
    def test_only_one_default_address_per_customer(self):
        customer = create_customer()
        Address.objects.create(
            customer=customer,
            address_name="Home",
            address_line="Plot 12",
            city="Dar es Salaam",
            phone="+255712000001",
            is_default=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Address.objects.create(
                    customer=customer,
                    address_name="Office",
                    address_line="Plot 20",
                    city="Dar es Salaam",
                    phone="+255712000001",
                    is_default=True,
                )

        Address.objects.create(
            customer=customer,
            address_name="Office",
            address_line="Plot 20",
            city="Dar es Salaam",
            phone="+255712000001",
            is_default=False,
        )
        self.assertEqual(customer.addresses.count(), 2)
