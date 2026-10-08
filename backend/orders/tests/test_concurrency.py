import threading

from django.db import connection
from django.test import TransactionTestCase

from cart import services as cart_services
from catalog.models import AvailabilityStatus
from core.errors import ApiError, ErrorCode
from core.testing.factories import AddressFactory, CustomerFactory, ProductFactory, StoreFactory
from orders import services
from orders.models import Order


def run_concurrently(callables):
    """Start every callable at the same moment on its own DB connection.
    Returns a list of ("ok", value) or ("error", exception) in the same order."""
    barrier = threading.Barrier(len(callables))
    results = [None] * len(callables)

    def worker(index, func):
        try:
            barrier.wait()
            results[index] = ("ok", func())
        except Exception as exc:
            results[index] = ("error", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=pair) for pair in enumerate(callables)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


class CheckoutConcurrencyTests(TransactionTestCase):
    def checkout_for(self, product, quantity=1):
        customer = CustomerFactory()
        address = AddressFactory(customer=customer)
        cart_services.add_item(customer, product.pk, quantity)
        return lambda: services.create_order(customer, address.pk, "CASH")

    def test_two_customers_cannot_both_buy_the_last_unit(self):
        last_one = ProductFactory(stock_quantity=1)
        checkouts = [self.checkout_for(last_one), self.checkout_for(last_one)]

        results = run_concurrently(checkouts)

        outcomes = sorted(kind for kind, _ in results)
        self.assertEqual(outcomes, ["error", "ok"], results)
        error = next(value for kind, value in results if kind == "error")
        self.assertIsInstance(error, ApiError)
        self.assertEqual(error.code, ErrorCode.INSUFFICIENT_STOCK)
        last_one.refresh_from_db()
        self.assertEqual(last_one.stock_quantity, 0)
        self.assertEqual(last_one.availability_status, AvailabilityStatus.OUT_OF_STOCK)
        self.assertEqual(Order.objects.count(), 1)

    def test_parallel_orders_get_distinct_numbers(self):
        stores = [StoreFactory() for _ in range(5)]
        checkouts = [self.checkout_for(ProductFactory(store=store)) for store in stores]

        results = run_concurrently(checkouts)

        self.assertTrue(all(kind == "ok" for kind, _ in results), results)
        numbers = sorted(order.order_number for _, order in results)
        self.assertEqual(len(set(numbers)), 5)
        self.assertEqual(
            [n.rsplit("-", 1)[1] for n in numbers], ["0001", "0002", "0003", "0004", "0005"]
        )
