from rest_framework import status
from rest_framework.test import APIClient

from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import StoreFactory
from core.testing.images import TemporaryMediaMixin, image_file
from core.validators import MAX_IMAGE_BYTES
from stores.models import Store, StoreStatus

LIST_URL = "/api/v1/owner/stores/"

NEW_STORE = {
    "store_name": "Upanga Drinks",
    "location": "Upanga Road, Dar es Salaam",
    "city": "Dar es Salaam",
    "area": "Upanga",
    "latitude": "-6.810000",
    "longitude": "39.285000",
    "phone": "+255713111222",
    "delivery_fee": "1500.00",
}


def detail_url(store):
    return f"/api/v1/owner/stores/{store.pk}/"


class OwnerStoreApiTests(TemporaryMediaMixin, ApiTestCase):
    def setUp(self):
        self.client_a, self.owner_a = self.store_owner_client()
        self.client_b, self.owner_b = self.store_owner_client()
        self.store_a = StoreFactory(owner=self.owner_a, store_name="A Store")
        self.store_b = StoreFactory(owner=self.owner_b, store_name="B Store")

    def test_lists_only_my_stores(self):
        StoreFactory(owner=self.owner_a, store_name="A Second", is_active=False)

        response = self.client_a.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [row["store_name"] for row in response.data["results"]], ["A Second", "A Store"]
        )

    def test_create_store(self):
        response = self.client_a.post(LIST_URL, {**NEW_STORE, "is_active": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        store = Store.objects.get(pk=response.data["id"])
        self.assertEqual(store.owner, self.owner_a)
        self.assertEqual(store.status, StoreStatus.CLOSED)
        self.assertTrue(store.is_active)
        self.assertEqual(response.data["delivery_fee"], "1500.00")

    def test_create_validation(self):
        cases = (
            ({"phone": "0713111222"}, "phone"),
            ({"delivery_fee": "-1.00"}, "delivery_fee"),
            ({"latitude": "-95.000000"}, "latitude"),
            ({"store_name": ""}, "store_name"),
        )
        for override, field in cases:
            with self.subTest(field=field):
                error = self.assertError(
                    self.client_a.post(LIST_URL, {**NEW_STORE, **override}, format="json"),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn(field, error["details"])

    def test_update_profile_status_and_fee(self):
        response = self.client_a.patch(
            detail_url(self.store_a),
            {"status": "OPEN", "delivery_fee": "3000.00", "description": "New"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store_a.refresh_from_db()
        self.assertEqual(self.store_a.status, StoreStatus.OPEN)
        self.assertEqual(str(self.store_a.delivery_fee), "3000.00")
        self.assertEqual(self.store_a.description, "New")

    def test_owner_cannot_change_is_active(self):
        response = self.client_a.patch(
            detail_url(self.store_a), {"is_active": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store_a.refresh_from_db()
        self.assertTrue(self.store_a.is_active)

    def test_put_is_not_allowed(self):
        self.assertError(
            self.client_a.put(detail_url(self.store_a), NEW_STORE, format="json"),
            status.HTTP_405_METHOD_NOT_ALLOWED,
            ErrorCode.METHOD_NOT_ALLOWED,
        )

    def test_other_owners_store_is_404(self):
        for method in ("get", "patch"):
            with self.subTest(method=method):
                response = getattr(self.client_b, method)(
                    detail_url(self.store_a), {"store_name": "Taken"}, format="json"
                )
                self.assertError(response, status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

        self.store_a.refresh_from_db()
        self.assertEqual(self.store_a.store_name, "A Store")

    def test_customer_and_anonymous_are_rejected(self):
        customer_client, _customer = self.customer_client()

        self.assertError(
            customer_client.get(LIST_URL), status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED
        )
        self.assertError(
            APIClient().get(LIST_URL), status.HTTP_401_UNAUTHORIZED, ErrorCode.NOT_AUTHENTICATED
        )

    def test_logo_upload(self):
        response = self.client_a.patch(
            detail_url(self.store_a), {"logo": image_file("logo.webp", "WEBP")}, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["logo"].startswith("http://testserver/media/stores/logos/"))

    def test_logo_rejects_bad_files(self):
        for upload in (
            image_file("logo.gif", "GIF"),
            image_file("logo.png", padding_bytes=MAX_IMAGE_BYTES),
        ):
            with self.subTest(name=upload.name, size=upload.size):
                error = self.assertError(
                    self.client_a.patch(
                        detail_url(self.store_a), {"logo": upload}, format="multipart"
                    ),
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                )
                self.assertIn("logo", error["details"])

    def test_list_query_count(self):
        StoreFactory.create_batch(5, owner=self.owner_a)

        # JWT user lookup, count, select
        with self.assertNumQueries(3):
            response = self.client_a.get(LIST_URL)

        self.assertEqual(response.data["count"], 6)
