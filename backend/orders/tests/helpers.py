from cart import services as cart_services
from core.testing.factories import AddressFactory
from orders import services


def fill_cart(customer, *lines):
    """lines: (product, quantity) pairs."""
    for product, quantity in lines:
        cart_services.add_item(customer, product.pk, quantity)


def place_order(customer, *lines, payment_method="CASH", address=None, **kwargs):
    fill_cart(customer, *lines)
    address = address or AddressFactory(customer=customer)
    return services.create_order(customer, address.pk, payment_method, **kwargs)
