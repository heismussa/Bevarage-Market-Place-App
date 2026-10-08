"""The whole order journey through the public API, the way the app will drive it."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.testing.factories import CategoryFactory

PASSWORD = "Kinywaji-Baridi-2026"


class OrderFlowEndToEndTests(APITestCase):
    def setUp(self):
        self.soda = CategoryFactory(name="Soda", slug="soda")

    def call(self, client, method, url, data=None, expected=status.HTTP_200_OK):
        """One request, with post-commit work (notifications) run as in production."""
        with self.captureOnCommitCallbacks(execute=True):
            response = getattr(client, method)(url, data, format="json")
        self.assertEqual(response.status_code, expected, response.content)
        return response.data

    def sign_up(self, full_name, phone, role):
        anonymous = APIClient()
        user = self.call(
            anonymous,
            "post",
            "/api/v1/auth/register/",
            {"full_name": full_name, "phone": phone, "password": PASSWORD, "role": role},
            expected=status.HTTP_201_CREATED,
        )
        self.assertEqual(user["role"], role)
        tokens = self.call(
            anonymous, "post", "/api/v1/auth/login/", {"phone": phone, "password": PASSWORD}
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return client

    def notification_types(self, client):
        page = self.call(client, "get", "/api/v1/notifications/")
        return sorted(row["notification_type"] for row in page["results"])

    def test_full_order_flow(self):
        customer = self.sign_up("Amina Hassan", "+255712000101", "CUSTOMER")
        owner = self.sign_up("Juma Mrisho", "+255712000102", "STORE_OWNER")

        # Store owner opens a store and lists a product.
        store = self.call(
            owner,
            "post",
            "/api/v1/owner/stores/",
            {
                "store_name": "Mlimani Drinks",
                "location": "Mlimani City, Sam Nujoma Road",
                "city": "Dar es Salaam",
                "area": "Ubungo",
                "latitude": "-6.772900",
                "longitude": "39.220400",
                "phone": "+255713000101",
                "status": "OPEN",
                "delivery_fee": "2000.00",
            },
            expected=status.HTTP_201_CREATED,
        )
        product = self.call(
            owner,
            "post",
            f"/api/v1/owner/stores/{store['id']}/products/",
            {
                "category": self.soda.pk,
                "name": "Coca-Cola 500ml",
                "unit": "BOTTLE",
                "price": "1500.00",
                "stock_quantity": 8,
                "low_stock_threshold": 5,
            },
            expected=status.HTTP_201_CREATED,
        )
        self.assertEqual(product["availability_status"], "AVAILABLE")

        # Customer browses, fills the cart and checks out with cash.
        stores = self.call(
            customer, "get", "/api/v1/stores/?lat=-6.7800&lng=39.2300&ordering=distance"
        )
        self.assertEqual([row["id"] for row in stores["results"]], [store["id"]])
        self.assertIsNotNone(stores["results"][0]["distance_km"])
        products = self.call(customer, "get", f"/api/v1/stores/{store['id']}/products/")
        self.assertEqual(products["results"][0]["id"], product["id"])

        address = self.call(
            customer,
            "post",
            "/api/v1/addresses/",
            {
                "address_name": "Home",
                "address_line": "Plot 5, Shekilango Road",
                "city": "Dar es Salaam",
                "area": "Sinza",
                "phone": "+255712000101",
            },
            expected=status.HTTP_201_CREATED,
        )
        self.assertTrue(address["is_default"])
        cart = self.call(
            customer,
            "post",
            "/api/v1/cart/items/",
            {"product_id": product["id"], "quantity": 3},
            expected=status.HTTP_201_CREATED,
        )
        self.assertEqual(cart["total"], "6500.00")

        order = self.call(
            customer,
            "post",
            "/api/v1/orders/",
            {"address_id": address["id"], "payment_method": "CASH", "total_amount": "1.00"},
            expected=status.HTTP_201_CREATED,
        )
        self.assertEqual(order["order_status"], "PENDING")
        self.assertEqual(order["total_amount"], "6500.00")
        self.assertEqual(order["allowed_actions"], ["cancel"])
        self.assertEqual(self.call(customer, "get", "/api/v1/cart/")["items"], [])
        self.assertEqual(self.notification_types(customer), ["ORDER_RECEIVED"])
        # 8 -> 5 reaches the threshold, so the owner is warned once.
        self.assertEqual(self.notification_types(owner), ["LOW_STOCK", "ORDER_RECEIVED"])

        # Store owner works the order to completion.
        expected_customer = ["ORDER_RECEIVED"]
        steps = (
            ("accept", "ACCEPTED", ["prepare", "cancel"]),
            ("prepare", "PREPARING", ["ready", "cancel"]),
            ("ready", "READY", ["complete"]),
            ("complete", "COMPLETED", []),
        )
        for action, new_status, next_actions in steps:
            with self.subTest(action=action):
                detail = self.call(
                    owner,
                    "post",
                    f"/api/v1/owner/orders/{order['id']}/transition/",
                    {"action": action},
                )
                self.assertEqual(detail["order_status"], new_status)
                self.assertEqual(detail["allowed_actions"], next_actions)
                expected_customer.append(f"ORDER_{new_status}")
                self.assertEqual(self.notification_types(customer), sorted(expected_customer))

        # Final state as each side sees it.
        final = self.call(customer, "get", f"/api/v1/orders/{order['id']}/")
        self.assertEqual(final["payment_status"], "SUCCESS")
        self.assertEqual(final["payment"]["payment_status"], "SUCCESS")
        self.assertEqual(
            [entry["status"] for entry in final["status_history"]],
            ["PENDING", "ACCEPTED", "PREPARING", "READY", "COMPLETED"],
        )
        self.assertEqual(self.notification_types(owner), ["LOW_STOCK", "ORDER_RECEIVED"])
        stock = self.call(owner, "get", f"/api/v1/owner/products/{product['id']}/")
        self.assertEqual(stock["stock_quantity"], 5)
        self.assertTrue(stock["is_low_stock"])
        dashboard = self.call(owner, "get", f"/api/v1/owner/stores/{store['id']}/dashboard/")
        self.assertEqual(Decimal(dashboard["total_sales"]), Decimal("6500.00"))
        self.assertEqual(dashboard["pending_orders"], 0)
        self.assertEqual(
            self.call(customer, "get", "/api/v1/notifications/unread-count/"),
            {"unread_count": 5},
        )
