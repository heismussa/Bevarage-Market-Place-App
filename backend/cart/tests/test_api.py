from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import ProductFactory, StoreFactory

CART_URL = "/api/v1/cart/"
ITEMS_URL = "/api/v1/cart/items/"


def item_url(item_id):
    return f"{ITEMS_URL}{item_id}/"


class CartApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()
        self.store = StoreFactory(store_name="ABC Drinks", delivery_fee=Decimal("2000.00"))
        self.cola = ProductFactory(store=self.store, price=Decimal("1500.00"), stock_quantity=10)

    def add(self, product, quantity=1, query=""):
        return self.client.post(
            ITEMS_URL + query, {"product_id": product.pk, "quantity": quantity}, format="json"
        )

    def test_empty_cart(self):
        response = self.client.get(CART_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "store": None,
                "items": [],
                "item_count": 0,
                "subtotal": "0.00",
                "delivery_fee": "0.00",
                "total": "0.00",
                "warnings": [],
            },
        )

    def test_add_returns_priced_cart(self):
        response = self.add(self.cola, 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["store"]["store_name"], "ABC Drinks")
        line = response.data["items"][0]
        self.assertEqual(line["name"], self.cola.name)
        self.assertEqual(line["unit"], "BOTTLE")
        self.assertEqual(line["unit_price"], "1500.00")
        self.assertEqual(line["quantity"], 2)
        self.assertEqual(line["line_total"], "3000.00")
        self.assertEqual(line["max_available"], 10)
        self.assertTrue(line["available"])
        self.assertFalse(line["price_changed"])
        self.assertEqual(response.data["item_count"], 2)
        self.assertEqual(response.data["subtotal"], "3000.00")
        self.assertEqual(response.data["delivery_fee"], "2000.00")
        self.assertEqual(response.data["total"], "5000.00")

    def test_client_prices_are_ignored(self):
        response = self.client.post(
            ITEMS_URL,
            {"product_id": self.cola.pk, "quantity": 1, "unit_price": "1.00", "total": "1.00"},
            format="json",
        )

        self.assertEqual(response.data["items"][0]["unit_price"], "1500.00")
        self.assertEqual(response.data["total"], "3500.00")
        self.assertEqual(CartItem.objects.get().unit_price, Decimal("1500.00"))

    def test_add_validation(self):
        for payload in ({"product_id": self.cola.pk, "quantity": 0}, {"quantity": 1}):
            with self.subTest(payload=payload):
                self.assertError(
                    self.client.post(ITEMS_URL, payload, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )

    def test_unknown_product_is_404(self):
        self.assertError(
            self.client.post(ITEMS_URL, {"product_id": 999999}, format="json"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )

    def test_stock_limit(self):
        self.add(self.cola, 8)

        error = self.assertError(
            self.add(self.cola, 3), status.HTTP_409_CONFLICT, ErrorCode.INSUFFICIENT_STOCK
        )

        self.assertEqual(error["details"]["max_available"], 10)
        self.assertEqual(self.client.get(CART_URL).data["items"][0]["quantity"], 8)

    def test_store_conflict_then_replace(self):
        self.add(self.cola)
        other = ProductFactory(store=StoreFactory(store_name="Masaki Beverages"))

        error = self.assertError(
            self.add(other), status.HTTP_409_CONFLICT, ErrorCode.CART_STORE_CONFLICT
        )
        self.assertEqual(error["details"]["cart_store_name"], "ABC Drinks")
        self.assertEqual(error["details"]["product_store_name"], "Masaki Beverages")

        response = self.add(other, query="?replace=true")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["store"]["store_name"], "Masaki Beverages")
        self.assertEqual([line["product_id"] for line in response.data["items"]], [other.pk])

    def test_price_change_is_flagged(self):
        self.add(self.cola, 2)
        self.cola.price = Decimal("1750.00")
        self.cola.save()

        data = self.client.get(CART_URL).data

        line = data["items"][0]
        self.assertTrue(line["price_changed"])
        self.assertEqual(line["price_when_added"], "1500.00")
        self.assertEqual(line["unit_price"], "1750.00")
        self.assertEqual(data["subtotal"], "3500.00")
        self.assertEqual(data["warnings"][0]["code"], "PRICE_CHANGED")

    def test_patch_quantity(self):
        item_id = self.add(self.cola).data["items"][0]["id"]

        response = self.client.patch(item_url(item_id), {"quantity": 4}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["quantity"], 4)
        self.assertError(
            self.client.patch(item_url(item_id), {"quantity": 11}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.INSUFFICIENT_STOCK,
        )
        self.assertError(
            self.client.patch(item_url(item_id), {"quantity": 0}, format="json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )

    def test_delete_last_item_releases_store(self):
        item_id = self.add(self.cola).data["items"][0]["id"]

        response = self.client.delete(item_url(item_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["store"])
        self.assertIsNone(Cart.objects.get(customer=self.customer).store)

    def test_clear_cart(self):
        self.add(self.cola, 2)

        response = self.client.delete(CART_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertIsNone(Cart.objects.get(customer=self.customer).store)

    def test_customers_cannot_see_or_change_each_others_carts(self):
        other_client, _ = self.customer_client()
        other_item_id = other_client.post(
            ITEMS_URL, {"product_id": self.cola.pk, "quantity": 3}, format="json"
        ).data["items"][0]["id"]

        self.assertEqual(self.client.get(CART_URL).data["items"], [])
        for method in ("patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    item_url(other_item_id), {"quantity": 1}, format="json"
                )
                self.assertError(response, status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

        self.client.delete(CART_URL)
        self.assertEqual(other_client.get(CART_URL).data["items"][0]["quantity"], 3)

    def test_store_owner_and_anonymous_are_rejected(self):
        owner_client, _ = self.store_owner_client()

        self.assertError(
            owner_client.get(CART_URL), status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED
        )
        self.assertError(
            APIClient().post(ITEMS_URL, {"product_id": self.cola.pk}, format="json"),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.NOT_AUTHENTICATED,
        )

    def test_get_query_count_does_not_grow_with_items(self):
        for _ in range(5):
            self.add(ProductFactory(store=self.store))

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(CART_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 5)
        self.assertEqual(len(queries), 4)
