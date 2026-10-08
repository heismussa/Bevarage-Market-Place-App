from decimal import Decimal

from django.http import Http404
from django.test import TestCase

from cart import services
from cart.models import Cart, CartItem
from catalog.models import AvailabilityStatus, CategoryStatus
from core.errors import ApiError, ErrorCode
from core.testing.factories import CustomerFactory, ProductFactory, StoreFactory
from stores.models import StoreStatus


class CartMutationTests(TestCase):
    def setUp(self):
        self.customer = CustomerFactory()
        self.store = StoreFactory()
        self.product = ProductFactory(store=self.store, stock_quantity=5)

    def assertApiError(self, code, func, *args, **kwargs):
        with self.assertRaises(ApiError) as caught:
            func(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.status_code, 409)
        return caught.exception

    def test_first_add_sets_cart_store_and_snapshot_price(self):
        cart = services.add_item(self.customer, self.product.pk, 2)

        self.assertEqual(cart.store, self.store)
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("1500.00"))

    def test_adding_same_product_increases_quantity(self):
        services.add_item(self.customer, self.product.pk, 2)
        services.add_item(self.customer, self.product.pk, 3)

        self.assertEqual(CartItem.objects.get().quantity, 5)

    def test_cannot_exceed_stock_including_quantity_already_in_cart(self):
        services.add_item(self.customer, self.product.pk, 4)

        error = self.assertApiError(
            ErrorCode.INSUFFICIENT_STOCK, services.add_item, self.customer, self.product.pk, 2
        )
        self.assertEqual(error.details["max_available"], 5)
        self.assertEqual(CartItem.objects.get().quantity, 4)

    def test_product_and_store_checks(self):
        cases = (
            (ProductFactory(deleted_at="2026-10-01T10:00:00Z"), ErrorCode.PRODUCT_UNAVAILABLE),
            (
                ProductFactory(availability_status=AvailabilityStatus.UNAVAILABLE),
                ErrorCode.PRODUCT_UNAVAILABLE,
            ),
            (
                ProductFactory(
                    stock_quantity=0, availability_status=AvailabilityStatus.OUT_OF_STOCK
                ),
                ErrorCode.INSUFFICIENT_STOCK,
            ),
            (
                ProductFactory(category__status=CategoryStatus.INACTIVE),
                ErrorCode.PRODUCT_UNAVAILABLE,
            ),
            (ProductFactory(store__status=StoreStatus.CLOSED), ErrorCode.STORE_CLOSED),
            (ProductFactory(store__is_active=False), ErrorCode.STORE_CLOSED),
        )
        for product, code in cases:
            with self.subTest(code=code, product=product.name):
                self.assertApiError(code, services.add_item, self.customer, product.pk, 1)
        self.assertFalse(CartItem.objects.exists())

    def test_unknown_product_is_not_found(self):
        with self.assertRaises(Http404):
            services.add_item(self.customer, 999999, 1)

    def test_other_store_conflicts_unless_replace(self):
        services.add_item(self.customer, self.product.pk, 1)
        other = ProductFactory()

        error = self.assertApiError(
            ErrorCode.CART_STORE_CONFLICT, services.add_item, self.customer, other.pk, 1
        )
        self.assertEqual(error.details["cart_store_id"], self.store.pk)
        self.assertEqual(error.details["product_store_id"], other.store_id)

        cart = services.add_item(self.customer, other.pk, 1, replace=True)

        self.assertEqual(cart.store, other.store)
        self.assertEqual(list(CartItem.objects.values_list("product_id", flat=True)), [other.pk])

    def test_replace_does_not_clear_when_new_product_is_rejected(self):
        services.add_item(self.customer, self.product.pk, 1)
        closed = ProductFactory(store__status=StoreStatus.CLOSED)

        self.assertApiError(
            ErrorCode.STORE_CLOSED, services.add_item, self.customer, closed.pk, 1, replace=True
        )
        self.assertEqual(CartItem.objects.get().product, self.product)

    def test_update_quantity_checks_stock(self):
        cart = services.add_item(self.customer, self.product.pk, 1)
        item = cart.items.get()

        services.update_item_quantity(self.customer, item.pk, 5)
        self.assertApiError(
            ErrorCode.INSUFFICIENT_STOCK,
            services.update_item_quantity,
            self.customer,
            item.pk,
            6,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_removing_last_item_clears_store(self):
        cart = services.add_item(self.customer, self.product.pk, 1)
        second = ProductFactory(store=self.store)
        services.add_item(self.customer, second.pk, 1)

        services.remove_item(self.customer, cart.items.get(product=self.product).pk)
        cart.refresh_from_db()
        self.assertEqual(cart.store, self.store)

        services.remove_item(self.customer, cart.items.get().pk)
        cart.refresh_from_db()
        self.assertIsNone(cart.store)

    def test_clear_cart(self):
        services.add_item(self.customer, self.product.pk, 1)

        cart = services.clear_cart(self.customer)

        self.assertIsNone(Cart.objects.get(pk=cart.pk).store)
        self.assertFalse(CartItem.objects.exists())

    def test_cannot_touch_another_customers_item(self):
        other_cart = services.add_item(CustomerFactory(), self.product.pk, 1)

        with self.assertRaises(Http404):
            services.remove_item(self.customer, other_cart.items.get().pk)
        self.assertTrue(CartItem.objects.exists())


class PriceCartTests(TestCase):
    def setUp(self):
        self.customer = CustomerFactory()
        self.store = StoreFactory(delivery_fee=Decimal("2500.00"))

    def summary(self):
        return services.price_cart(services.load_cart(self.customer))

    def test_missing_cart_is_empty_and_zero(self):
        summary = self.summary()

        self.assertIsNone(summary.store)
        self.assertEqual(summary.lines, [])
        self.assertEqual(summary.total, Decimal("0.00"))

    def test_totals_use_current_prices(self):
        cola = ProductFactory(store=self.store, price=Decimal("1500.00"))
        juice = ProductFactory(store=self.store, price=Decimal("2350.50"))
        services.add_item(self.customer, cola.pk, 3)
        services.add_item(self.customer, juice.pk, 2)
        cola.price = Decimal("1600.00")
        cola.save()

        summary = self.summary()

        lines = {line.item.product_id: line for line in summary.lines}
        self.assertEqual(lines[cola.pk].line_total, Decimal("4800.00"))
        self.assertTrue(lines[cola.pk].price_changed)
        self.assertEqual(lines[juice.pk].line_total, Decimal("4701.00"))
        self.assertFalse(lines[juice.pk].price_changed)
        self.assertEqual(summary.subtotal, Decimal("9501.00"))
        self.assertEqual(summary.delivery_fee, Decimal("2500.00"))
        self.assertEqual(summary.total, Decimal("12001.00"))
        self.assertEqual([w["code"] for w in summary.warnings], ["PRICE_CHANGED"])

    def test_readding_acknowledges_new_price(self):
        cola = ProductFactory(store=self.store, price=Decimal("1500.00"))
        services.add_item(self.customer, cola.pk, 1)
        cola.price = Decimal("1600.00")
        cola.save()

        services.add_item(self.customer, cola.pk, 1)

        self.assertFalse(self.summary().lines[0].price_changed)

    def test_warnings_for_problems_after_adding(self):
        low = ProductFactory(store=self.store, stock_quantity=5)
        hidden = ProductFactory(store=self.store)
        services.add_item(self.customer, low.pk, 4)
        services.add_item(self.customer, hidden.pk, 1)
        low.stock_quantity = 2
        low.save()
        hidden.availability_status = AvailabilityStatus.UNAVAILABLE
        hidden.save()

        summary = self.summary()

        lines = {line.item.product_id: line for line in summary.lines}
        self.assertTrue(lines[low.pk].available)
        self.assertEqual(lines[low.pk].max_available, 2)
        self.assertFalse(lines[hidden.pk].available)
        self.assertEqual(lines[hidden.pk].max_available, 0)
        self.assertEqual(
            sorted(w["code"] for w in summary.warnings),
            ["INSUFFICIENT_STOCK", "PRODUCT_UNAVAILABLE"],
        )
        self.assertFalse(lines[low.pk].counted_in_total)
        self.assertFalse(lines[hidden.pk].counted_in_total)
        self.assertEqual(summary.subtotal, Decimal("0.00"))
        self.assertEqual(summary.delivery_fee, Decimal("0.00"))
        self.assertEqual(summary.total, Decimal("0.00"))

    def test_only_buyable_lines_count_toward_totals(self):
        cola = ProductFactory(store=self.store, price=Decimal("1500.00"))
        fanta = ProductFactory(store=self.store, price=Decimal("1500.00"))
        services.add_item(self.customer, cola.pk, 2)
        services.add_item(self.customer, fanta.pk, 1)
        fanta.availability_status = AvailabilityStatus.UNAVAILABLE
        fanta.save()

        summary = self.summary()

        lines = {line.item.product_id: line for line in summary.lines}
        self.assertTrue(lines[cola.pk].counted_in_total)
        self.assertFalse(lines[fanta.pk].counted_in_total)
        self.assertEqual(lines[fanta.pk].line_total, Decimal("1500.00"))
        self.assertEqual(summary.subtotal, Decimal("3000.00"))
        self.assertEqual(summary.delivery_fee, Decimal("2500.00"))
        self.assertEqual(summary.total, Decimal("5500.00"))

    def test_sold_out_line_reports_insufficient_stock(self):
        cola = ProductFactory(store=self.store, stock_quantity=2)
        services.add_item(self.customer, cola.pk, 1)
        cola.stock_quantity = 0
        cola.availability_status = AvailabilityStatus.OUT_OF_STOCK
        cola.save()

        summary = self.summary()

        self.assertFalse(summary.lines[0].available)
        self.assertEqual(summary.lines[0].max_available, 0)
        self.assertEqual(summary.warnings[0]["code"], "INSUFFICIENT_STOCK")
        self.assertEqual(summary.warnings[0]["message"], f"{cola.name} is sold out.")

    def test_closed_store_warning(self):
        product = ProductFactory(store=self.store)
        services.add_item(self.customer, product.pk, 1)
        self.store.status = StoreStatus.CLOSED
        self.store.save()

        summary = self.summary()

        self.assertEqual(summary.warnings[0]["code"], "STORE_CLOSED")
        self.assertIsNone(summary.warnings[0]["item_id"])
        self.assertFalse(summary.lines[0].available)
        self.assertEqual(summary.total, Decimal("0.00"))
