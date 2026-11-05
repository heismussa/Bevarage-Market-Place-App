from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import AvailabilityStatus, CategoryStatus
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import (
    CategoryFactory,
    OrderFactory,
    OrderItemFactory,
    ProductFactory,
    StoreFactory,
)
from orders.models import Order, OrderStatus
from stores.models import StoreStatus


def names(response):
    return [row["name"] for row in response.data["results"]]


class CategoryListTests(ApiTestCase):
    def test_only_active_categories(self):
        CategoryFactory(name="Soda")
        CategoryFactory(name="Beer")
        CategoryFactory(name="Retired", status=CategoryStatus.INACTIVE)

        with self.assertNumQueries(2):
            response = APIClient().get("/api/v1/categories/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["name"] for row in response.data["results"]], ["Beer", "Soda"])


class StoreProductListTests(ApiTestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = StoreFactory()
        self.soda = CategoryFactory(name="Soda")
        self.water = CategoryFactory(name="Water")
        self.cola = ProductFactory(
            store=self.store, category=self.soda, name="Cola", price=Decimal("1500.00")
        )
        self.water_bottle = ProductFactory(
            store=self.store, category=self.water, name="Water 1.5L", price=Decimal("1000.00")
        )
        self.empty = ProductFactory(
            store=self.store,
            category=self.soda,
            name="Fanta",
            price=Decimal("1600.00"),
            stock_quantity=0,
            availability_status=AvailabilityStatus.OUT_OF_STOCK,
        )
        ProductFactory(store=self.store, category=self.soda, name="Gone", deleted_at=timezone.now())
        ProductFactory(
            store=self.store,
            category=CategoryFactory(status=CategoryStatus.INACTIVE),
            name="Retired category",
        )
        ProductFactory(category=self.soda, name="Other store")
        self.url = f"/api/v1/stores/{self.store.pk}/products/"

    def test_excludes_deleted_products_and_inactive_categories(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(names(response), ["Cola", "Fanta", "Water 1.5L"])
        first = response.data["results"][0]
        self.assertEqual(first["price"], "1500.00")
        self.assertEqual(first["category"], {"id": self.soda.pk, "name": "Soda", "slug": "soda"})
        self.assertEqual(first["store_name"], self.store.store_name)

    def test_filters(self):
        cases = (
            (f"?category={self.water.pk}", ["Water 1.5L"]),
            ("?search=cola", ["Cola"]),
            ("?availability=OUT_OF_STOCK", ["Fanta"]),
            ("?in_stock=true", ["Cola", "Water 1.5L"]),
            ("?in_stock=false", ["Fanta"]),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(names(self.client.get(self.url + query)), expected)

    def test_ordering(self):
        self.assertEqual(
            names(self.client.get(self.url + "?ordering=price")), ["Water 1.5L", "Cola", "Fanta"]
        )
        self.assertEqual(
            names(self.client.get(self.url + "?ordering=-price")), ["Fanta", "Cola", "Water 1.5L"]
        )
        self.assertEqual(
            names(self.client.get(self.url + "?ordering=-name")), ["Water 1.5L", "Fanta", "Cola"]
        )

    def test_inactive_or_missing_store_is_404(self):
        hidden = StoreFactory(is_active=False)
        for url in (f"/api/v1/stores/{hidden.pk}/products/", "/api/v1/stores/999999/products/"):
            with self.subTest(url=url):
                self.assertError(
                    self.client.get(url), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND
                )

    def test_query_count_does_not_grow_with_rows(self):
        ProductFactory.create_batch(8, store=self.store)

        # store lookup, count, select (with store and category joined)
        with self.assertNumQueries(3):
            response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 11)


class PopularProductTests(ApiTestCase):
    url = "/api/v1/products/popular/"

    def sell(self, product, quantity, order_status=OrderStatus.COMPLETED, days_ago=0):
        order = OrderFactory(store=product.store, order_status=order_status)
        if days_ago:
            Order.objects.filter(pk=order.pk).update(
                ordered_at=timezone.now() - timedelta(days=days_ago)
            )
        OrderItemFactory(order=order, product=product, quantity=quantity)

    def popular(self, query=""):
        response = APIClient().get(self.url + query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [(row["name"], row["sold_quantity"]) for row in response.data["results"]]

    def test_best_sellers_first_and_unsold_left_out(self):
        store = StoreFactory()
        cola = ProductFactory(store=store, name="Cola")
        juice = ProductFactory(store=store, name="Juice")
        ProductFactory(store=store, name="Water")
        self.sell(cola, 2)
        self.sell(cola, 1)
        self.sell(juice, 5)
        self.sell(cola, 50, order_status=OrderStatus.PENDING)
        self.sell(cola, 50, order_status=OrderStatus.CANCELLED)
        self.sell(cola, 50, days_ago=31)

        self.assertEqual(self.popular(), [("Juice", 5), ("Cola", 3)])

    def test_only_products_customers_can_buy_now(self):
        hidden = (
            ProductFactory(store=StoreFactory(status=StoreStatus.CLOSED)),
            ProductFactory(store=StoreFactory(is_active=False)),
            ProductFactory(stock_quantity=0, availability_status=AvailabilityStatus.OUT_OF_STOCK),
            ProductFactory(availability_status=AvailabilityStatus.UNAVAILABLE),
            ProductFactory(deleted_at=timezone.now()),
            ProductFactory(category=CategoryFactory(status=CategoryStatus.INACTIVE)),
        )
        for product in hidden:
            self.sell(product, 3)
        self.sell(ProductFactory(name="Visible"), 1)

        self.assertEqual(self.popular(), [("Visible", 1)])

    def test_store_and_category_filters(self):
        soda = CategoryFactory(name="Soda")
        cola = ProductFactory(name="Cola", category=soda)
        lager = ProductFactory(name="Lager")
        self.sell(cola, 1)
        self.sell(lager, 2)

        self.assertEqual(self.popular(f"?store={cola.store_id}"), [("Cola", 1)])
        self.assertEqual(self.popular(f"?category={soda.pk}"), [("Cola", 1)])

    def test_query_count_does_not_grow_with_rows(self):
        for _ in range(6):
            self.sell(ProductFactory(), 1)

        # count, select (with store and category joined)
        with self.assertNumQueries(2):
            response = APIClient().get(self.url)

        self.assertEqual(response.data["count"], 6)


class ProductDetailTests(ApiTestCase):
    def test_visible_product(self):
        product = ProductFactory(name="Cola")

        response = APIClient().get(f"/api/v1/products/{product.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Cola")
        self.assertTrue(response.data["in_stock"])

    def test_hidden_products_are_404(self):
        hidden = (
            ProductFactory(deleted_at=timezone.now()),
            ProductFactory(store=StoreFactory(is_active=False)),
            ProductFactory(category=CategoryFactory(status=CategoryStatus.INACTIVE)),
        )
        for product in hidden:
            with self.subTest(product=product.name):
                self.assertError(
                    APIClient().get(f"/api/v1/products/{product.pk}/"),
                    status.HTTP_404_NOT_FOUND,
                    ErrorCode.NOT_FOUND,
                )
