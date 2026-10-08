from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from payments.choices import PaymentMethod
from payments.providers import get_provider, provider_for_method
from payments.providers.base import InvalidWebhookPayload
from payments.providers.cash import CashProvider
from payments.providers.mock import SIGNATURE_HEADER, MockMobileMoneyProvider, build_webhook


@override_settings(MOCK_PAYMENT_WEBHOOK_SECRET="test-secret", MOBILE_MONEY_PROVIDER="mock")
class RegistryTests(SimpleTestCase):
    def test_methods_map_to_providers(self):
        self.assertIsInstance(provider_for_method(PaymentMethod.CASH), CashProvider)
        for method in (PaymentMethod.MPESA, PaymentMethod.TIGO_PESA, PaymentMethod.AIRTEL_MONEY):
            with self.subTest(method=method):
                self.assertIsInstance(provider_for_method(method), MockMobileMoneyProvider)
        self.assertIsNone(provider_for_method(PaymentMethod.CARD))

    @override_settings(MOBILE_MONEY_PROVIDER="missing")
    def test_unconfigured_mobile_provider(self):
        self.assertIsNone(provider_for_method(PaymentMethod.MPESA))

    def test_real_gateway_is_not_registered(self):
        self.assertIsNone(get_provider("real_gateway"))


@override_settings(MOCK_PAYMENT_WEBHOOK_SECRET="test-secret")
class MockProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = MockMobileMoneyProvider()

    def test_signed_webhook_verifies_and_parses(self):
        body, headers = build_webhook("MOCK-1", amount=Decimal("5000.00"))

        self.assertTrue(self.provider.verify_webhook(body, headers))
        event = self.provider.parse_event(body)
        self.assertEqual(event.transaction_reference, "MOCK-1")
        self.assertTrue(event.succeeded)
        self.assertEqual(event.amount, Decimal("5000.00"))

    def test_tampered_body_or_signature_fails(self):
        body, headers = build_webhook("MOCK-1", amount=Decimal("5000.00"))

        self.assertFalse(self.provider.verify_webhook(body.replace(b"5000", b"9000"), headers))
        self.assertFalse(self.provider.verify_webhook(body, {SIGNATURE_HEADER: "0" * 64}))
        self.assertFalse(self.provider.verify_webhook(body, {}))

    def test_empty_secret_rejects_everything(self):
        body, headers = build_webhook("MOCK-1", amount=Decimal("1.00"))

        with override_settings(MOCK_PAYMENT_WEBHOOK_SECRET=""):
            self.assertFalse(self.provider.verify_webhook(body, headers))

    def test_malformed_bodies(self):
        for body in (b"not json", b"{}", b'{"reference":"X","status":"MAYBE","amount":"1"}'):
            with self.subTest(body=body), self.assertRaises(InvalidWebhookPayload):
                self.provider.parse_event(body)
