from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.errors import ErrorCode
from core.testing.api import ApiTestCase, authenticated_client
from core.testing.factories import ProductFactory, StoreFactory
from orders import services as order_services
from orders.models import OrderStatus, OrderStatusHistory
from orders.state_machine import Action
from orders.tests.helpers import place_order
from payments.choices import PaymentStatus
from payments.models import Payment
from payments.providers.mock import SIGNATURE_HEADER, sign
from payments.tests.helpers import WEBHOOK_URL, latest, send_webhook


def pay_url(order):
    return f"/api/v1/orders/{order.pk}/pay/"


def payment_url(order):
    return f"/api/v1/orders/{order.pk}/payment/"


def refund_notes(order):
    return list(
        OrderStatusHistory.objects.filter(order=order, notes__startswith="REFUND_REQUIRED")
        .order_by("id")
        .values_list("notes", flat=True)
    )


@override_settings(MOCK_PAYMENT_WEBHOOK_SECRET="test-secret", MOBILE_MONEY_PROVIDER="mock")
class PaymentTestCase(ApiTestCase):
    def setUp(self):
        cache.clear()
        self.client, self.customer = self.customer_client()
        self.store = StoreFactory(delivery_fee=Decimal("2000.00"))
        self.owner_client = authenticated_client(self.store.owner.user)
        self.cola = ProductFactory(store=self.store, price=Decimal("1500.00"), stock_quantity=10)
        self.webhook_client = APIClient()

    def mobile_order(self, quantity=2):
        return place_order(self.customer, (self.cola, quantity), payment_method="MPESA")

    def start_payment(self, order):
        response = self.client.post(pay_url(order), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["payment"]["transaction_reference"]


class PayEndpointTests(PaymentTestCase):
    def test_pay_sends_prompt_but_never_marks_success(self):
        order = self.mobile_order()

        response = self.client.post(pay_url(order), {"payer_phone": "+255799000111"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = response.data["payment"]
        self.assertEqual(payment["payment_status"], "PROCESSING")
        self.assertTrue(payment["transaction_reference"].startswith("MOCK-"))
        self.assertEqual(payment["payer_phone"], "+255799000111")
        self.assertIn("+255799000111", response.data["instructions"])
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.PROCESSING)
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    def test_second_pay_while_processing_is_rejected(self):
        order = self.mobile_order()
        self.start_payment(order)

        self.assertError(
            self.client.post(pay_url(order), {}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.PAYMENT_IN_PROGRESS,
        )

    def test_cash_and_closed_orders_cannot_be_paid(self):
        cash = place_order(self.customer, (self.cola, 1))
        cancelled = self.mobile_order()
        order_services.transition_order(cancelled, Action.CANCEL, self.customer.user)

        for order in (cash, cancelled):
            with self.subTest(order=order.order_number):
                self.assertError(
                    self.client.post(pay_url(order), {}, format="json"),
                    status.HTTP_409_CONFLICT,
                    ErrorCode.PAYMENT_NOT_ALLOWED,
                )

    def test_paid_order_cannot_be_paid_again(self):
        order = self.mobile_order()
        send_webhook(self.webhook_client, self.start_payment(order), amount="5000.00")

        self.assertError(
            self.client.post(pay_url(order), {}, format="json"),
            status.HTTP_409_CONFLICT,
            ErrorCode.PAYMENT_NOT_ALLOWED,
        )

    def test_other_customers_order_is_not_found(self):
        order = self.mobile_order()
        other_client, _ = self.customer_client()

        for request in (
            lambda: other_client.post(pay_url(order), {}, format="json"),
            lambda: other_client.get(payment_url(order)),
        ):
            self.assertError(request(), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

    @override_settings(PAYMENT_INITIATION_RATE="2/min")
    def test_pay_is_rate_limited(self):
        order = self.mobile_order()
        self.client.post(pay_url(order), {}, format="json")
        self.client.post(pay_url(order), {}, format="json")

        error = self.assertError(
            self.client.post(pay_url(order), {}, format="json"),
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.THROTTLED,
        )
        self.assertIn("wait_seconds", error["details"])

    def test_payment_status_endpoint(self):
        order = self.mobile_order()
        reference = self.start_payment(order)

        response = self.client.get(payment_url(order))

        self.assertEqual(response.data["transaction_reference"], reference)
        self.assertEqual(response.data["payment_status"], "PROCESSING")
        self.assertEqual(response.data["amount"], "5000.00")


class WebhookTests(PaymentTestCase):
    def test_success_marks_payment_and_order_paid(self):
        order = self.mobile_order()
        reference = self.start_payment(order)

        response = send_webhook(self.webhook_client, reference, amount="5000.00")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data, {"received": True, "payment_status": "SUCCESS"})
        payment = latest(order)
        self.assertEqual(payment.payment_status, PaymentStatus.SUCCESS)
        self.assertIsNotNone(payment.payment_time)
        self.assertEqual(payment.gateway_response["reference"], reference)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.SUCCESS)

    def test_duplicate_webhook_changes_nothing(self):
        order = self.mobile_order()
        reference = self.start_payment(order)
        send_webhook(self.webhook_client, reference, amount="5000.00")
        first_time = latest(order).payment_time
        history_count = order.status_history.count()

        again = send_webhook(self.webhook_client, reference, amount="5000.00")
        conflicting = send_webhook(
            self.webhook_client, reference, succeeded=False, amount="5000.00"
        )

        for response in (again, conflicting):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["payment_status"], "SUCCESS")
        payment = latest(order)
        self.assertEqual(payment.payment_status, PaymentStatus.SUCCESS)
        self.assertEqual(payment.payment_time, first_time)
        self.assertEqual(order.status_history.count(), history_count)

    def test_wrong_amount_fails_payment_and_flags_refund(self):
        order = self.mobile_order()
        reference = self.start_payment(order)

        response = send_webhook(self.webhook_client, reference, amount="7000.00")

        self.assertEqual(response.data["payment_status"], "FAILED")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.FAILED)
        self.assertEqual(order.order_status, OrderStatus.PENDING)
        notes = refund_notes(order)
        self.assertEqual(len(notes), 1)
        self.assertIn("7000.00", notes[0])

    def test_bad_or_missing_signature(self):
        order = self.mobile_order()
        reference = self.start_payment(order)

        for headers in ({SIGNATURE_HEADER: "f" * 64}, {}):
            with self.subTest(headers=headers):
                self.assertError(
                    send_webhook(self.webhook_client, reference, amount="5000.00", headers=headers),
                    status.HTTP_401_UNAUTHORIZED,
                    ErrorCode.INVALID_SIGNATURE,
                )
        self.assertEqual(latest(order).payment_status, PaymentStatus.PROCESSING)

    def test_unknown_provider_reference_and_bad_body(self):
        self.assertError(
            self.webhook_client.post(
                "/api/v1/payments/webhook/nope/", data=b"{}", content_type="application/json"
            ),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        self.assertError(
            send_webhook(self.webhook_client, "MOCK-UNKNOWN", amount="1.00"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        body = b"not json"
        self.assertError(
            self.webhook_client.post(
                WEBHOOK_URL,
                data=body,
                content_type="application/json",
                headers={SIGNATURE_HEADER: sign(body)},
            ),
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
        )

    def test_retry_after_failure_then_success(self):
        order = self.mobile_order()
        first = self.start_payment(order)
        send_webhook(self.webhook_client, first, succeeded=False, amount="5000.00")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.FAILED)

        second = self.start_payment(order)
        send_webhook(self.webhook_client, second, amount="5000.00")

        self.assertNotEqual(first, second)
        statuses = list(
            Payment.objects.filter(order=order)
            .order_by("id")
            .values_list("payment_status", flat=True)
        )
        self.assertEqual(statuses, ["FAILED", "SUCCESS"])
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.SUCCESS)

    def test_second_successful_payment_is_flagged_for_refund(self):
        order = self.mobile_order()
        send_webhook(self.webhook_client, self.start_payment(order), amount="5000.00")
        duplicate = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method="MPESA",
            payment_status=PaymentStatus.PROCESSING,
            transaction_reference="MOCK-DUPLICATE",
        )

        send_webhook(self.webhook_client, duplicate.transaction_reference, amount="5000.00")

        duplicate.refresh_from_db()
        self.assertEqual(duplicate.payment_status, PaymentStatus.SUCCESS)
        self.assertIn("second payment", refund_notes(order)[0])

    def test_payment_after_cancellation_is_flagged_for_refund(self):
        order = self.mobile_order()
        reference = self.start_payment(order)
        self.client.post(f"/api/v1/orders/{order.pk}/cancel/", {}, format="json")

        send_webhook(self.webhook_client, reference, amount="5000.00")

        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.CANCELLED)
        self.assertEqual(order.payment_status, PaymentStatus.SUCCESS)
        self.assertIn("after the order was CANCELLED", refund_notes(order)[0])

    def test_owner_cancelling_a_paid_order_flags_refund(self):
        order = self.mobile_order()
        send_webhook(self.webhook_client, self.start_payment(order), amount="5000.00")
        self.owner_client.post(
            f"/api/v1/owner/orders/{order.pk}/transition/", {"action": "accept"}, format="json"
        )

        self.owner_client.post(
            f"/api/v1/owner/orders/{order.pk}/transition/",
            {"action": "cancel", "reason": "Crate broke"},
            format="json",
        )

        notes = refund_notes(order)
        self.assertEqual(len(notes), 1)
        self.assertIn("Crate broke", notes[0])


class OwnerVisibilityAndCashTests(PaymentTestCase):
    def owner_ids(self):
        response = self.owner_client.get(f"/api/v1/owner/stores/{self.store.pk}/orders/")
        return [row["id"] for row in response.data["results"]]

    def test_mobile_orders_hidden_until_paid_cash_visible_at_once(self):
        cash = place_order(self.customer, (self.cola, 1))
        mobile = self.mobile_order()

        self.assertEqual(self.owner_ids(), [cash.pk])
        self.assertError(
            self.owner_client.get(f"/api/v1/owner/orders/{mobile.pk}/"),
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
        )
        dashboard = self.owner_client.get(f"/api/v1/owner/stores/{self.store.pk}/dashboard/")
        self.assertEqual(dashboard.data["total_orders"], 1)

        send_webhook(self.webhook_client, self.start_payment(mobile), amount="5000.00")

        self.assertEqual(self.owner_ids(), [mobile.pk, cash.pk])

    def test_cash_becomes_success_when_completed(self):
        order = place_order(self.customer, (self.cola, 1))
        url = f"/api/v1/owner/orders/{order.pk}/transition/"

        for action in ("accept", "prepare", "ready"):
            self.owner_client.post(url, {"action": action}, format="json")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)

        response = self.owner_client.post(url, {"action": "complete"}, format="json")

        self.assertEqual(response.data["payment_status"], "SUCCESS")
        payment = latest(order)
        self.assertEqual(payment.payment_status, PaymentStatus.SUCCESS)
        self.assertIsNotNone(payment.payment_time)
