from decimal import Decimal

from django.db import connection, transaction
from django.db.models import F
from django.db.models.functions import Length
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import Address
from cart.models import Cart
from cart.services import stock_message
from catalog.models import AvailabilityStatus, CategoryStatus, Product
from catalog.services import sync_availability
from core.errors import ApiError, ErrorCode
from notifications.services import notify_if_became_low
from orders import events
from orders.models import Order, OrderItem, OrderStatus, OrderStatusHistory
from orders.state_machine import (
    STOCK_RESTORING_STATUSES,
    Actor,
    actor_for,
    allowed_actions,
    find_transition,
)
from payments import services as payment_services
from payments.choices import MOBILE_MONEY_METHODS, PaymentStatus
from payments.models import Payment
from stores.models import StoreStatus

CENT = Decimal("0.01")
ORDER_NUMBER_PREFIX = "BDM"
# Namespace for pg_advisory_xact_lock(namespace, yyyymmdd) so the key cannot collide with
# advisory locks taken for other purposes.
ORDER_NUMBER_LOCK_NAMESPACE = 7301


def _conflict(code, message, details=None):
    return ApiError(code, message, status_code=status.HTTP_409_CONFLICT, details=details)


# --- Order number ---------------------------------------------------------------------


def next_order_number():
    """BDM-YYYYMMDD-NNNN, numbered per local day. Must run inside a transaction.

    A transaction-scoped advisory lock per day serializes number allocation, so two
    checkouts can never read the same "last number". The unique constraint on
    order_number remains the final safety net.
    """
    today = timezone.localdate()
    day_key = int(today.strftime("%Y%m%d"))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)", [ORDER_NUMBER_LOCK_NAMESPACE, day_key]
        )
    prefix = f"{ORDER_NUMBER_PREFIX}-{day_key}-"
    last = (
        Order.objects.filter(order_number__startswith=prefix)
        .order_by(Length("order_number").desc(), "-order_number")
        .values_list("order_number", flat=True)
        .first()
    )
    sequence = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{sequence:04d}"


# --- Checkout -------------------------------------------------------------------------


def _address_snapshot(address):
    parts = [address.address_line, address.area, address.city]
    return ", ".join(part for part in parts if part)[:255]


def _line_problem(product, quantity, store_id):
    # OUT_OF_STOCK is reported by the stock check below as INSUFFICIENT_STOCK.
    if (
        product.deleted_at is not None
        or product.store_id != store_id
        or product.category.status != CategoryStatus.ACTIVE
        or product.availability_status == AvailabilityStatus.UNAVAILABLE
    ):
        return {
            "code": str(ErrorCode.PRODUCT_UNAVAILABLE),
            "product_id": product.pk,
            "name": product.name,
        }
    if quantity > product.stock_quantity:
        return {
            "code": str(ErrorCode.INSUFFICIENT_STOCK),
            "product_id": product.pk,
            "name": product.name,
            "requested": quantity,
            "max_available": product.stock_quantity,
        }
    return None


@transaction.atomic
def create_order(customer, address_id, payment_method, payer_phone=None, notes=None):
    """Turn the customer's cart into an order. All prices come from the database."""
    # 1. Lock the cart and its items.
    cart = Cart.objects.select_for_update().filter(customer=customer).first()
    items = list(cart.items.select_for_update().order_by("id")) if cart else []
    if not items:
        raise _conflict(ErrorCode.EMPTY_CART, "Your cart is empty.")

    # 2. Store must be active and open; address must be the customer's.
    store = cart.store
    if store is None or not store.is_active or store.status != StoreStatus.OPEN:
        raise _conflict(
            ErrorCode.STORE_CLOSED,
            "This store is not accepting orders right now.",
            {"store_id": cart.store_id},
        )
    address = Address.objects.filter(pk=address_id, customer=customer).first()
    if address is None:
        raise ValidationError({"address_id": ["Select one of your saved addresses."]})

    # 3. Lock products in id order so concurrent checkouts cannot deadlock.
    quantities = {item.product_id: item.quantity for item in items}
    products = list(
        Product.objects.select_for_update(of=("self",))
        .select_related("category")
        .filter(pk__in=quantities)
        .order_by("id")
    )

    # 4. Validate every line and report all problems at once.
    problems = [
        problem
        for product in products
        if (problem := _line_problem(product, quantities[product.pk], store.pk))
    ]
    if problems:
        first = problems[0]
        if first["code"] == ErrorCode.PRODUCT_UNAVAILABLE:
            message = f"{first['name']} is not available."
        else:
            message = stock_message(first["name"], first["max_available"])
        raise _conflict(first["code"], message, {"problems": problems})

    # 5. Recompute money from the database.
    lines = []
    subtotal = Decimal("0.00")
    for product in products:
        quantity = quantities[product.pk]
        line_total = (product.price * quantity).quantize(CENT)
        subtotal += line_total
        lines.append((product, quantity, line_total))
    delivery_fee = store.delivery_fee.quantize(CENT)
    total = (subtotal + delivery_fee).quantize(CENT)

    # 6. Order and item snapshots.
    order = Order.objects.create(
        order_number=next_order_number(),
        customer=customer,
        store=store,
        address=address,
        delivery_address=_address_snapshot(address),
        delivery_phone=address.phone,
        delivery_latitude=address.latitude,
        delivery_longitude=address.longitude,
        subtotal_amount=subtotal,
        delivery_fee=delivery_fee,
        total_amount=total,
        order_status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        notes=notes or None,
    )
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=product,
            product_name=product.name,
            unit=product.unit,
            quantity=quantity,
            unit_price=product.price,
            subtotal=line_total,
        )
        for product, quantity, line_total in lines
    )

    # 7. Take the stock. Products are locked, so their loaded stock is the "before" value.
    for product, quantity, _ in lines:
        Product.objects.filter(pk=product.pk).update(
            stock_quantity=F("stock_quantity") - quantity, updated_at=timezone.now()
        )
        before = product.stock_quantity
        product.stock_quantity -= quantity
        product.store = store
        notify_if_became_low(product, before, product.low_stock_threshold)
    sync_availability(Product.objects.filter(pk__in=quantities))

    # 8. History, 9. payment.
    OrderStatusHistory.objects.create(
        order=order, from_status=None, status=OrderStatus.PENDING, changed_by=customer.user
    )
    if payment_method in MOBILE_MONEY_METHODS and not payer_phone:
        payer_phone = customer.user.phone
    Payment.objects.create(
        order=order,
        amount=total,
        payment_method=payment_method,
        payment_status=PaymentStatus.PENDING,
        payer_phone=payer_phone or None,
    )

    # 10. Empty the cart. A double submit now fails with EMPTY_CART.
    cart.items.all().delete()
    cart.store = None
    cart.save(update_fields=["store", "updated_at"])

    transaction.on_commit(lambda: events.notify_order_event(order, events.ORDER_CREATED))
    return order


# --- Transitions ----------------------------------------------------------------------


def _ensure_visible(order, user, actor):
    """Services enforce ownership too, so a caller cannot act on an order it cannot see."""
    visible = (
        actor in (Actor.ADMIN, Actor.SYSTEM)
        or (actor == Actor.CUSTOMER and order.customer_id == user.pk)
        or (actor == Actor.STORE_OWNER and order.store.owner_id == user.pk)
    )
    if not visible:
        raise NotFound()


def _restore_stock(order):
    quantities = {}
    for product_id, quantity in order.items.values_list("product_id", "quantity"):
        quantities[product_id] = quantities.get(product_id, 0) + quantity
    locked = Product.objects.select_for_update().filter(pk__in=quantities).order_by("id")
    for product_id in locked.values_list("pk", flat=True):
        Product.objects.filter(pk=product_id).update(
            stock_quantity=F("stock_quantity") + quantities[product_id],
            updated_at=timezone.now(),
        )
    sync_availability(Product.objects.filter(pk__in=quantities))


@transaction.atomic
def transition_order(order, action, actor_user, reason=None):
    """Apply one state-machine action. Locks the order so each change happens once."""
    order = Order.objects.select_for_update(of=("self",)).select_related("store").get(pk=order.pk)
    actor = actor_for(actor_user)
    if actor is None:
        raise NotFound()
    _ensure_visible(order, actor_user, actor)

    transition = find_transition(order.order_status, action, actor)
    if transition is None:
        raise _conflict(
            ErrorCode.INVALID_TRANSITION,
            f"You cannot {action} an order that is {order.order_status}.",
            {
                "order_status": order.order_status,
                "action": str(action),
                "allowed_actions": allowed_actions(order.order_status, actor),
            },
        )

    reason = (reason or "").strip() or None
    if transition.reason_required and reason is None:
        raise ValidationError({"reason": ["A reason is required for this action."]})

    previous = order.order_status
    order.order_status = transition.target
    update_fields = ["order_status", "updated_at"]
    notes = reason
    if transition.target in STOCK_RESTORING_STATUSES:
        order.status_reason = reason
        _restore_stock(order)
        if order.payment_status == PaymentStatus.SUCCESS:
            notes = f"{payment_services.REFUND_REQUIRED}: order was paid. {reason or ''}".strip()
        payment_services.cancel_unstarted_payments(order)
        update_fields += ["status_reason", "payment_status"]
    elif transition.target == OrderStatus.COMPLETED:
        if payment_services.collect_cash_on_completion(order):
            update_fields.append("payment_status")
    order.save(update_fields=update_fields)

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous,
        status=transition.target,
        changed_by=actor_user,
        notes=notes,
    )
    event = events.status_event(transition.target)
    transaction.on_commit(lambda: events.notify_order_event(order, event, actor))
    return order
