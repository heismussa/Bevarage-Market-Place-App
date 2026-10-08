from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status

from cart.models import Cart, CartItem
from catalog.models import AvailabilityStatus, CategoryStatus, Product
from core.errors import ApiError, ErrorCode
from stores.models import StoreStatus

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

# Cart warnings reuse the matching error codes; PRICE_CHANGED exists only as a warning.
PRICE_CHANGED = "PRICE_CHANGED"


def _money(value):
    return Decimal(value).quantize(CENT)


# --- Validation -----------------------------------------------------------------------


def stock_message(name, max_available):
    if max_available <= 0:
        return f"{name} is sold out."
    return f"Only {max_available} of {name} left in stock."


def _product_problem(product):
    """Return (code, message) when the product cannot be bought right now, else None.
    Stock is checked separately because it depends on the requested quantity, so a
    sold-out (OUT_OF_STOCK) product is reported as INSUFFICIENT_STOCK."""
    store = product.store
    if not store.is_active or store.status != StoreStatus.OPEN:
        return ErrorCode.STORE_CLOSED, f"{store.store_name} is not accepting orders right now."
    if (
        product.deleted_at is not None
        or product.category.status != CategoryStatus.ACTIVE
        or product.availability_status == AvailabilityStatus.UNAVAILABLE
    ):
        return ErrorCode.PRODUCT_UNAVAILABLE, f"{product.name} is not available."
    return None


def _ensure_sellable(product):
    problem = _product_problem(product)
    if problem is not None:
        code, message = problem
        raise ApiError(
            code,
            message,
            status_code=status.HTTP_409_CONFLICT,
            details={"product_id": product.pk, "store_id": product.store_id},
        )


def _ensure_in_stock(product, quantity):
    if quantity > product.stock_quantity:
        raise ApiError(
            ErrorCode.INSUFFICIENT_STOCK,
            stock_message(product.name, product.stock_quantity),
            status_code=status.HTTP_409_CONFLICT,
            details={
                "product_id": product.pk,
                "requested": quantity,
                "max_available": product.stock_quantity,
            },
        )


# --- Mutations ------------------------------------------------------------------------


def _lock_cart(customer):
    """Return the customer's cart, row-locked for the rest of the transaction."""
    cart, _ = Cart.objects.select_for_update().get_or_create(customer=customer)
    return cart


def _release_store_if_empty(cart):
    if cart.store_id is not None and not cart.items.exists():
        cart.store = None
        cart.save(update_fields=["store", "updated_at"])


def _get_product(product_id):
    return get_object_or_404(Product.objects.select_related("store", "category"), pk=product_id)


@transaction.atomic
def add_item(customer, product_id, quantity, *, replace=False):
    """Add quantity of a product. An existing line is increased, not duplicated.

    A cart holds products from one store only. Adding from another store raises
    CART_STORE_CONFLICT unless replace=True, which empties the cart first.
    """
    cart = _lock_cart(customer)
    product = _get_product(product_id)
    _ensure_sellable(product)

    has_items = cart.items.exists()
    if has_items and cart.store_id != product.store_id:
        if not replace:
            raise ApiError(
                ErrorCode.CART_STORE_CONFLICT,
                "Your cart has items from another store. Clear it to add this product.",
                status_code=status.HTTP_409_CONFLICT,
                details={
                    "cart_store_id": cart.store_id,
                    "cart_store_name": cart.store.store_name,
                    "product_store_id": product.store_id,
                    "product_store_name": product.store.store_name,
                },
            )
        cart.items.all().delete()

    item = cart.items.filter(product=product).first()
    new_quantity = quantity + (item.quantity if item else 0)
    _ensure_in_stock(product, new_quantity)

    if item is None:
        CartItem.objects.create(
            cart=cart, product=product, quantity=new_quantity, unit_price=product.price
        )
    else:
        item.quantity = new_quantity
        item.unit_price = product.price
        item.save(update_fields=["quantity", "unit_price", "updated_at"])

    if cart.store_id != product.store_id:
        cart.store = product.store
    cart.save(update_fields=["store", "updated_at"])
    return cart


@transaction.atomic
def update_item_quantity(customer, item_id, quantity):
    cart = _lock_cart(customer)
    item = get_object_or_404(cart.items.all(), pk=item_id)
    product = _get_product(item.product_id)
    _ensure_sellable(product)
    _ensure_in_stock(product, quantity)
    item.quantity = quantity
    item.unit_price = product.price
    item.save(update_fields=["quantity", "unit_price", "updated_at"])
    cart.save(update_fields=["updated_at"])
    return cart


@transaction.atomic
def remove_item(customer, item_id):
    cart = _lock_cart(customer)
    get_object_or_404(cart.items.all(), pk=item_id).delete()
    _release_store_if_empty(cart)
    cart.save(update_fields=["updated_at"])
    return cart


@transaction.atomic
def clear_cart(customer):
    cart = _lock_cart(customer)
    cart.items.all().delete()
    _release_store_if_empty(cart)
    return cart


# --- Pricing --------------------------------------------------------------------------


@dataclass
class CartLine:
    item: CartItem
    line_total: Decimal
    price_changed: bool
    available: bool
    max_available: int
    counted_in_total: bool


@dataclass
class CartSummary:
    store: object
    lines: list
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    warnings: list = field(default_factory=list)


def _warning(code, message, item_id=None):
    return {"code": str(code), "message": message, "item_id": item_id}


def load_cart(customer):
    """The customer's cart with everything price_cart needs, or None if never created."""
    items = CartItem.objects.select_related("product__store", "product__category").order_by("id")
    return (
        Cart.objects.select_related("store")
        .prefetch_related(Prefetch("items", queryset=items))
        .filter(customer=customer)
        .first()
    )


def price_cart(cart):
    """Price the cart from CURRENT product prices. The stored unit_price is only used to
    detect price changes since the item was added.

    Only lines the customer can buy right now (available, quantity within stock) count
    toward the subtotal. The delivery fee is charged only when at least one line counts.
    """
    if cart is None:
        return CartSummary(store=None, lines=[], subtotal=ZERO, delivery_fee=ZERO, total=ZERO)

    lines = []
    warnings = []
    subtotal = ZERO
    for item in cart.items.all():
        product = item.product
        problem = _product_problem(product)
        available = problem is None and product.stock_quantity > 0
        counted = available and item.quantity <= product.stock_quantity
        line_total = _money(product.price * item.quantity)
        price_changed = item.unit_price != product.price
        if counted:
            subtotal += line_total
        lines.append(
            CartLine(
                item=item,
                line_total=line_total,
                price_changed=price_changed,
                available=available,
                max_available=product.stock_quantity if available else 0,
                counted_in_total=counted,
            )
        )
        if problem is not None and problem[0] == ErrorCode.PRODUCT_UNAVAILABLE:
            warnings.append(_warning(problem[0], problem[1], item.pk))
        elif problem is None and item.quantity > product.stock_quantity:
            warnings.append(
                _warning(
                    ErrorCode.INSUFFICIENT_STOCK,
                    stock_message(product.name, product.stock_quantity),
                    item.pk,
                )
            )
        if price_changed:
            warnings.append(
                _warning(
                    PRICE_CHANGED,
                    f"The price of {product.name} changed from {item.unit_price} "
                    f"to {product.price}.",
                    item.pk,
                )
            )

    store = cart.store if lines else None
    if store is not None and (not store.is_active or store.status != StoreStatus.OPEN):
        warnings.insert(
            0,
            _warning(
                ErrorCode.STORE_CLOSED, f"{store.store_name} is not accepting orders right now."
            ),
        )
    has_buyable_lines = any(line.counted_in_total for line in lines)
    delivery_fee = _money(store.delivery_fee) if has_buyable_lines else ZERO
    return CartSummary(
        store=store,
        lines=lines,
        subtotal=_money(subtotal),
        delivery_fee=delivery_fee,
        total=_money(subtotal + delivery_fee),
        warnings=warnings,
    )
