import math
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import CategoryStatus
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import CategoryFactory, ProductFactory, StoreFactory
from stores.models import StoreStatus

LIST_URL = "/api/v1/stores/"

KARIAKOO = (Decimal("-6.823490"), Decimal("39.274530"))
MASAKI = (Decimal("-6.747800"), Decimal("39.279200"))
MBEZI = (Decimal("-6.720000"), Decimal("39.180000"))


def haversine_km(a, b):
    lat1, lng1, lat2, lng2 = map(math.radians, (*map(float, a), *map(float, b)))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def names(response):
    return [row["store_name"] for row in response.data["results"]]


class PublicStoreListTests(ApiTestCase):
    def setUp(self):
        self.client = APIClient()
        self.kariakoo = StoreFactory(
            store_name="Kariakoo Drinks",
            area="Kariakoo",
            latitude=KARIAKOO[0],
            longitude=KARIAKOO[1],
        )
        self.masaki = StoreFactory(
            store_name="Masaki Beverages",
            area="Masaki",
            latitude=MASAKI[0],
            longitude=MASAKI[1],
            status=StoreStatus.CLOSED,
        )
        self.mbezi = StoreFactory(
            store_name="Mbezi Wines",
            area="Mbezi",
            city="Dar es Salaam",
            latitude=MBEZI[0],
            longitude=MBEZI[1],
        )
        self.no_location = StoreFactory(
            store_name="Arusha Juice", city="Arusha", area="Central", latitude=None, longitude=None
        )
        self.inactive = StoreFactory(store_name="Hidden Store", is_active=False)

    def test_lists_only_active_stores(self):
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            names(response),
            ["Arusha Juice", "Kariakoo Drinks", "Masaki Beverages", "Mbezi Wines"],
        )
        self.assertIsNone(response.data["results"][0]["distance_km"])

    def test_filters(self):
        cases = (
            ("?status=CLOSED", ["Masaki Beverages"]),
            ("?city=arusha", ["Arusha Juice"]),
            ("?area=MASAKI", ["Masaki Beverages"]),
            ("?search=wines", ["Mbezi Wines"]),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(names(self.client.get(LIST_URL + query)), expected)

    def test_category_filter_ignores_deleted_products_and_inactive_categories(self):
        soda = CategoryFactory(name="Soda")
        wine = CategoryFactory(name="Wine", status=CategoryStatus.INACTIVE)
        ProductFactory(store=self.kariakoo, category=soda)
        ProductFactory(store=self.masaki, category=soda, deleted_at="2026-10-01T10:00:00Z")
        ProductFactory(store=self.mbezi, category=wine)

        self.assertEqual(
            names(self.client.get(f"{LIST_URL}?category={soda.pk}")), ["Kariakoo Drinks"]
        )
        self.assertEqual(names(self.client.get(f"{LIST_URL}?category={wine.pk}")), [])

    def test_distance_is_annotated_and_orderable(self):
        response = self.client.get(
            f"{LIST_URL}?lat={KARIAKOO[0]}&lng={KARIAKOO[1]}&ordering=distance"
        )

        self.assertEqual(
            names(response),
            ["Kariakoo Drinks", "Masaki Beverages", "Mbezi Wines", "Arusha Juice"],
        )
        distances = {row["store_name"]: row["distance_km"] for row in response.data["results"]}
        self.assertEqual(distances["Kariakoo Drinks"], 0.0)
        self.assertAlmostEqual(distances["Masaki Beverages"], haversine_km(KARIAKOO, MASAKI), 2)
        self.assertAlmostEqual(distances["Mbezi Wines"], haversine_km(KARIAKOO, MBEZI), 2)
        self.assertIsNone(distances["Arusha Juice"])

    def test_distance_descending(self):
        response = self.client.get(
            f"{LIST_URL}?lat={KARIAKOO[0]}&lng={KARIAKOO[1]}&ordering=-distance&city=Dar es Salaam"
        )

        self.assertEqual(names(response), ["Mbezi Wines", "Masaki Beverages", "Kariakoo Drinks"])

    def test_distance_ordering_requires_coordinates(self):
        error = self.assertError(
            self.client.get(f"{LIST_URL}?ordering=distance"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("ordering", error["details"])

    def test_bad_coordinates(self):
        for query in ("?lat=-6.8", "?lat=200&lng=39", "?lat=abc&lng=39"):
            with self.subTest(query=query):
                self.assertError(
                    self.client.get(LIST_URL + query),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )

    def test_query_count_does_not_grow_with_rows(self):
        StoreFactory.create_batch(10)

        with self.assertNumQueries(2):
            response = self.client.get(f"{LIST_URL}?lat=-6.8&lng=39.2&ordering=distance")

        self.assertEqual(response.data["count"], 14)


class PublicStoreDetailTests(ApiTestCase):
    def test_active_store(self):
        store = StoreFactory(latitude=MASAKI[0], longitude=MASAKI[1])

        response = APIClient().get(
            f"/api/v1/stores/{store.pk}/?lat={KARIAKOO[0]}&lng={KARIAKOO[1]}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["store_name"], store.store_name)
        self.assertEqual(response.data["delivery_fee"], "2000.00")
        self.assertAlmostEqual(response.data["distance_km"], haversine_km(KARIAKOO, MASAKI), 2)

    def test_inactive_store_is_404(self):
        store = StoreFactory(is_active=False)

        self.assertError(
            APIClient().get(f"/api/v1/stores/{store.pk}/"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
