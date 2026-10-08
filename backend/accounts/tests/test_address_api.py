from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Address
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import AddressFactory

LIST_URL = "/api/v1/addresses/"

NEW_ADDRESS = {
    "address_name": "Home",
    "address_line": "Plot 12, Haile Selassie Road",
    "city": "Dar es Salaam",
    "area": "Msasani",
    "latitude": "-6.748900",
    "longitude": "39.276800",
    "phone": "+255712345678",
}


def detail_url(address):
    return f"{LIST_URL}{address.pk}/"


def set_default_url(address):
    return f"{LIST_URL}{address.pk}/set-default/"


class AddressApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()

    def test_first_address_is_default(self):
        response = self.client.post(LIST_URL, NEW_ADDRESS, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["is_default"])
        self.assertEqual(Address.objects.get().customer, self.customer)

    def test_second_address_is_not_default_even_if_requested(self):
        self.client.post(LIST_URL, NEW_ADDRESS, format="json")
        response = self.client.post(
            LIST_URL, {**NEW_ADDRESS, "address_name": "Office", "is_default": True}, format="json"
        )

        self.assertFalse(response.data["is_default"])
        self.assertEqual(Address.objects.filter(is_default=True).count(), 1)

    def test_create_validation(self):
        cases = (
            ({**NEW_ADDRESS, "phone": "0712345678"}, "phone"),
            ({**NEW_ADDRESS, "latitude": "-91"}, "latitude"),
            ({k: v for k, v in NEW_ADDRESS.items() if k != "longitude"}, "latitude"),
            ({k: v for k, v in NEW_ADDRESS.items() if k != "address_line"}, "address_line"),
        )
        for payload, field in cases:
            with self.subTest(field=field):
                error = self.assertError(
                    self.client.post(LIST_URL, payload, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn(field, error["details"])

    def test_list_shows_only_my_addresses_default_first(self):
        AddressFactory(customer=self.customer, address_name="B Office")
        default = AddressFactory(customer=self.customer, address_name="Z Home", is_default=True)
        AddressFactory(address_name="Someone else")

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], default.pk)

    def test_filters(self):
        AddressFactory(customer=self.customer, city="Arusha", is_default=True)
        AddressFactory(customer=self.customer, city="Dar es Salaam")

        by_city = self.client.get(f"{LIST_URL}?city=arusha")
        by_default = self.client.get(f"{LIST_URL}?is_default=false")

        self.assertEqual([row["city"] for row in by_city.data["results"]], ["Arusha"])
        self.assertEqual([row["city"] for row in by_default.data["results"]], ["Dar es Salaam"])

    def test_list_query_count_is_constant(self):
        AddressFactory.create_batch(5, customer=self.customer)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(queries), 3)

    def test_patch_updates_fields_but_not_is_default(self):
        address = AddressFactory(customer=self.customer, is_default=True)

        response = self.client.patch(
            detail_url(address), {"address_name": "Office", "is_default": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        address.refresh_from_db()
        self.assertEqual(address.address_name, "Office")
        self.assertTrue(address.is_default)

    def test_put_is_not_allowed(self):
        address = AddressFactory(customer=self.customer)

        self.assertError(
            self.client.put(detail_url(address), NEW_ADDRESS, format="json"),
            status.HTTP_405_METHOD_NOT_ALLOWED,
            ErrorCode.METHOD_NOT_ALLOWED,
        )

    def test_set_default(self):
        old = AddressFactory(customer=self.customer, is_default=True)
        new = AddressFactory(customer=self.customer)

        response = self.client.post(set_default_url(new))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_default"])
        old.refresh_from_db()
        self.assertFalse(old.is_default)

    def test_delete_default_promotes_most_recent(self):
        default = AddressFactory(customer=self.customer, is_default=True)
        AddressFactory(customer=self.customer)
        newest = AddressFactory(customer=self.customer)

        response = self.client.delete(detail_url(default))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        newest.refresh_from_db()
        self.assertTrue(newest.is_default)

    def test_other_customers_address_is_not_found(self):
        other = AddressFactory(is_default=True)
        requests = (
            ("get", detail_url(other)),
            ("patch", detail_url(other)),
            ("delete", detail_url(other)),
            ("post", set_default_url(other)),
        )
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {"city": "X"}, format="json")
                self.assertError(response, status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

        other.refresh_from_db()
        self.assertTrue(other.is_default)
        self.assertNotEqual(other.city, "X")

    def test_store_owner_and_anonymous_are_rejected(self):
        owner_client, _ = self.store_owner_client()

        self.assertError(
            owner_client.get(LIST_URL), status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED
        )
        self.assertError(
            APIClient().get(LIST_URL), status.HTTP_401_UNAUTHORIZED, ErrorCode.NOT_AUTHENTICATED
        )
