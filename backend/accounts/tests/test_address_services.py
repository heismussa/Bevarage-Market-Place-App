from django.test import TestCase

from accounts import services
from accounts.models import Address
from core.testing.factories import AddressFactory, CustomerFactory

DATA = {
    "address_name": "Home",
    "address_line": "Plot 12, Haile Selassie Road",
    "city": "Dar es Salaam",
    "phone": "+255712345678",
}


def default_ids(customer):
    return list(
        Address.objects.filter(customer=customer, is_default=True).values_list("pk", flat=True)
    )


class AddressServiceTests(TestCase):
    def setUp(self):
        self.customer = CustomerFactory()

    def test_first_address_becomes_default_and_later_ones_do_not(self):
        first = services.create_address(self.customer, DATA)
        second = services.create_address(self.customer, {**DATA, "address_name": "Office"})

        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)
        self.assertEqual(default_ids(self.customer), [first.pk])

    def test_set_default_moves_the_flag(self):
        first = services.create_address(self.customer, DATA)
        second = services.create_address(self.customer, {**DATA, "address_name": "Office"})

        result = services.set_default_address(second)

        self.assertTrue(result.is_default)
        self.assertEqual(default_ids(self.customer), [second.pk])
        first.refresh_from_db()
        self.assertFalse(first.is_default)

    def test_set_default_on_current_default_is_harmless(self):
        first = services.create_address(self.customer, DATA)

        services.set_default_address(first)

        self.assertEqual(default_ids(self.customer), [first.pk])

    def test_deleting_default_promotes_most_recent(self):
        default = services.create_address(self.customer, DATA)
        services.create_address(self.customer, {**DATA, "address_name": "Office"})
        newest = services.create_address(self.customer, {**DATA, "address_name": "Campus"})

        services.delete_address(default)

        self.assertEqual(default_ids(self.customer), [newest.pk])

    def test_deleting_non_default_keeps_default(self):
        default = services.create_address(self.customer, DATA)
        other = services.create_address(self.customer, {**DATA, "address_name": "Office"})

        services.delete_address(other)

        self.assertEqual(default_ids(self.customer), [default.pk])

    def test_deleting_last_address_leaves_none(self):
        only = services.create_address(self.customer, DATA)

        services.delete_address(only)

        self.assertFalse(Address.objects.filter(customer=self.customer).exists())

    def test_customers_do_not_affect_each_other(self):
        other_default = AddressFactory(is_default=True)
        mine = services.create_address(self.customer, DATA)

        self.assertTrue(mine.is_default)
        other_default.refresh_from_db()
        self.assertTrue(other_default.is_default)
