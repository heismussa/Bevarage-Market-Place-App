from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import AvailabilityStatus, CategoryStatus, Product
from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import CategoryFactory, ProductFactory, StoreFactory
from core.testing.images import TemporaryMediaMixin, image_file
from core.validators import MAX_IMAGE_BYTES

AVAILABLE = AvailabilityStatus.AVAILABLE
OUT_OF_STOCK = AvailabilityStatus.OUT_OF_STOCK
UNAVAILABLE = AvailabilityStatus.UNAVAILABLE


def store_products_url(store):
    return f"/api/v1/owner/stores/{store.pk}/products/"


def product_url(product):
    return f"/api/v1/owner/products/{product.pk}/"


def stock_url(product):
    return f"/api/v1/owner/products/{product.pk}/stock/"


def names(response):
    return [row["name"] for row in response.data["results"]]


class OwnerProductApiTests(TemporaryMediaMixin, ApiTestCase):
    def setUp(self):
        self.client_a, self.owner_a = self.store_owner_client()
        self.client_b, self.owner_b = self.store_owner_client()
        self.store_a = StoreFactory(owner=self.owner_a)
        self.store_b = StoreFactory(owner=self.owner_b)
        self.soda = CategoryFactory(name="Soda")
        self.product_a = ProductFactory(
            store=self.store_a, category=self.soda, name="Cola", stock_quantity=20
        )
        self.product_b = ProductFactory(store=self.store_b, category=self.soda, name="B Cola")
        self.new_product = {
            "category": self.soda.pk,
            "name": "Sprite 500ml",
            "unit": "CAN",
            "price": "1500.00",
            "stock_quantity": 30,
            "low_stock_threshold": 5,
        }

    # Ownership

    def test_other_owners_store_products_are_404(self):
        self.assertError(
            self.client_b.get(store_products_url(self.store_a)),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        self.assertError(
            self.client_b.post(store_products_url(self.store_a), self.new_product, format="json"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        self.assertFalse(Product.objects.filter(name="Sprite 500ml").exists())

    def test_other_owners_product_is_404_for_every_method(self):
        calls = (
            ("get", product_url(self.product_a), None),
            ("patch", product_url(self.product_a), {"price": "1.00"}),
            ("delete", product_url(self.product_a), None),
            ("patch", stock_url(self.product_a), {"stock_quantity": 0}),
        )
        for method, url, body in calls:
            with self.subTest(method=method, url=url):
                response = getattr(self.client_b, method)(url, body, format="json")
                self.assertError(response, status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.price, Decimal("1500.00"))
        self.assertEqual(self.product_a.stock_quantity, 20)
        self.assertIsNone(self.product_a.deleted_at)

    def test_customer_is_forbidden(self):
        customer_client, _customer = self.customer_client()

        self.assertError(
            customer_client.get(product_url(self.product_a)),
            status.HTTP_403_FORBIDDEN,
            ErrorCode.PERMISSION_DENIED,
        )

    def test_anonymous_is_unauthenticated(self):
        self.assertError(
            APIClient().get(store_products_url(self.store_a)),
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.NOT_AUTHENTICATED,
        )

    # List and filters

    def test_list_and_filters(self):
        ProductFactory(store=self.store_a, name="Low", stock_quantity=3, low_stock_threshold=5)
        ProductFactory(
            store=self.store_a, name="Hidden", availability_status=UNAVAILABLE, stock_quantity=9
        )
        ProductFactory(store=self.store_a, name="Deleted", deleted_at=timezone.now())

        cases = (
            ("", ["Cola", "Hidden", "Low"]),
            ("?low_stock=true", ["Low"]),
            ("?low_stock=false", ["Cola", "Hidden"]),
            ("?availability=UNAVAILABLE", ["Hidden"]),
            ("?search=col", ["Cola"]),
            ("?ordering=stock_quantity", ["Low", "Hidden", "Cola"]),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(
                    names(self.client_a.get(store_products_url(self.store_a) + query)), expected
                )

    def test_list_query_count(self):
        ProductFactory.create_batch(6, store=self.store_a)

        # JWT user, store ownership lookup, count, select (category joined)
        with self.assertNumQueries(4):
            response = self.client_a.get(store_products_url(self.store_a))

        self.assertEqual(response.data["count"], 7)

    # Create

    def test_create_product(self):
        response = self.client_a.post(
            store_products_url(self.store_a), self.new_product, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.store, self.store_a)
        self.assertEqual(product.availability_status, AVAILABLE)
        self.assertEqual(response.data["category_detail"]["name"], "Soda")

    def test_create_with_zero_stock_is_out_of_stock(self):
        response = self.client_a.post(
            store_products_url(self.store_a),
            {**self.new_product, "stock_quantity": 0},
            format="json",
        )

        self.assertEqual(response.data["availability_status"], OUT_OF_STOCK)

    def test_create_validation(self):
        inactive = CategoryFactory(status=CategoryStatus.INACTIVE)
        body_without_unit = {k: v for k, v in self.new_product.items() if k != "unit"}
        cases = (
            ({**self.new_product, "category": inactive.pk}, "category"),
            ({**self.new_product, "price": "0.00"}, "price"),
            ({**self.new_product, "price": "-5.00"}, "price"),
            (body_without_unit, "unit"),
            ({**self.new_product, "unit": "BARREL"}, "unit"),
            ({**self.new_product, "stock_quantity": -1}, "stock_quantity"),
            ({**self.new_product, "low_stock_threshold": -1}, "low_stock_threshold"),
            ({**self.new_product, "availability_status": "OUT_OF_STOCK"}, "availability_status"),
            ({**self.new_product, "name": "Cola"}, "name"),
        )
        for body, field in cases:
            with self.subTest(field=field, body=body):
                error = self.assertError(
                    self.client_a.post(store_products_url(self.store_a), body, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn(field, error["details"])

    def test_name_is_reusable_after_soft_delete(self):
        self.client_a.delete(product_url(self.product_a))

        response = self.client_a.post(
            store_products_url(self.store_a), {**self.new_product, "name": "Cola"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_image_upload(self):
        response = self.client_a.post(
            store_products_url(self.store_a),
            {**self.new_product, "image": image_file("sprite.jpg", "JPEG")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["image"].startswith("http://testserver/media/products/"))

    def test_image_rejects_bad_files(self):
        for upload in (
            image_file("sprite.gif", "GIF"),
            image_file("sprite.png", padding_bytes=MAX_IMAGE_BYTES),
        ):
            with self.subTest(name=upload.name):
                error = self.assertError(
                    self.client_a.patch(
                        product_url(self.product_a), {"image": upload}, format="multipart"
                    ),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn("image", error["details"])

    # Update

    def test_edit_product(self):
        response = self.client_a.patch(
            product_url(self.product_a),
            {"price": "1750.00", "availability_status": UNAVAILABLE},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.price, Decimal("1750.00"))
        self.assertEqual(self.product_a.availability_status, UNAVAILABLE)

    def test_editing_stock_to_zero_syncs_availability(self):
        response = self.client_a.patch(
            product_url(self.product_a), {"stock_quantity": 0}, format="json"
        )

        self.assertEqual(response.data["availability_status"], OUT_OF_STOCK)

    def test_rename_to_an_existing_name_is_rejected(self):
        ProductFactory(store=self.store_a, name="Fanta")

        error = self.assertError(
            self.client_a.patch(product_url(self.product_a), {"name": "Fanta"}, format="json"),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )
        self.assertIn("name", error["details"])

    # Stock endpoint and availability sync

    def test_stock_endpoint_syncs_availability(self):
        response = self.client_a.patch(
            stock_url(self.product_a), {"stock_quantity": 0}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["stock_quantity"], 0)
        self.assertEqual(response.data["availability_status"], OUT_OF_STOCK)

        response = self.client_a.patch(
            stock_url(self.product_a), {"stock_quantity": 15}, format="json"
        )
        self.assertEqual(response.data["availability_status"], AVAILABLE)

    def test_stock_keeps_unavailable_while_positive(self):
        self.client_a.patch(
            product_url(self.product_a), {"availability_status": UNAVAILABLE}, format="json"
        )

        response = self.client_a.patch(
            stock_url(self.product_a), {"stock_quantity": 40}, format="json"
        )

        self.assertEqual(response.data["availability_status"], UNAVAILABLE)

    def test_stock_validation(self):
        for body in ({"stock_quantity": -1}, {}, {"stock_quantity": "lots"}):
            with self.subTest(body=body):
                self.assertError(
                    self.client_a.patch(stock_url(self.product_a), body, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )

    # Soft delete

    def test_delete_is_soft_and_hides_the_product_everywhere(self):
        response = self.client_a.delete(product_url(self.product_a))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.product_a.refresh_from_db()
        self.assertIsNotNone(self.product_a.deleted_at)

        self.assertEqual(names(self.client_a.get(store_products_url(self.store_a))), [])
        self.assertError(
            self.client_a.get(product_url(self.product_a)),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        public = APIClient()
        self.assertEqual(names(public.get(f"/api/v1/stores/{self.store_a.pk}/products/")), [])
        self.assertError(
            public.get(f"/api/v1/products/{self.product_a.pk}/"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
