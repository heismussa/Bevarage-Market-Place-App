"""Order events turned into in-app notifications.

Callers schedule these with transaction.on_commit, so they only run after the change is
saved. Who is told what:

- ORDER_CREATED: the customer; the store owner too for cash orders.
- PAYMENT_SUCCESS: the customer; the store owner gets ORDER_RECEIVED now, because
  non-cash orders stay hidden from the store until paid.
- PAYMENT_FAILED: the customer.
- ORDER_<status>: the customer. A cancellation not made by the store owner also tells
  the store owner, if the store could see the order.
- LOW_STOCK: the store owner, once each time stock drops to or below the threshold.
"""

import logging

from notifications.models import NotificationType
from notifications.services import create_notification
from orders.models import OrderStatus
from orders.state_machine import Actor
from payments.choices import PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)

ORDER_CREATED = "ORDER_CREATED"
PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
PAYMENT_FAILED = "PAYMENT_FAILED"

STATUS_TEXT = {
    "ACCEPTED": ("Order accepted", "{store} accepted order {number}."),
    "REJECTED": ("Order rejected", "{store} rejected order {number}.{reason}"),
    "PREPARING": ("Order being prepared", "{store} is preparing order {number}."),
    "READY": ("Order ready", "Order {number} is ready."),
    "COMPLETED": ("Order completed", "Order {number} is complete. Enjoy!"),
    "CANCELLED": ("Order cancelled", "Order {number} was cancelled.{reason}"),
}


def status_event(status):
    """Event name for an order entering status, e.g. ORDER_ACCEPTED."""
    return f"ORDER_{status}"


def notify_order_event(order, event, actor=None):
    """Create the notifications for one event. Never raises: the change is already saved."""
    try:
        _dispatch(order, event, actor)
    except Exception:
        logger.exception("Could not notify %s for order %s", event, order.pk)


def _dispatch(order, event, actor):
    number = order.order_number
    if event == ORDER_CREATED:
        _to_customer(
            order,
            NotificationType.ORDER_RECEIVED,
            "Order placed",
            f"We sent order {number} to {order.store.store_name}.",
        )
        if _is_cash(order):
            _new_order_to_owner(order)
    elif event == PAYMENT_SUCCESS:
        _to_customer(
            order,
            NotificationType.PAYMENT_SUCCESS,
            "Payment received",
            f"We received {order.total_amount} TZS for order {number}.",
        )
        if order.order_status == OrderStatus.PENDING:
            _new_order_to_owner(order)
    elif event == PAYMENT_FAILED:
        _to_customer(
            order,
            NotificationType.PAYMENT_FAILED,
            "Payment failed",
            f"Payment for order {number} did not go through. You can try again.",
        )
    else:
        status = event.removeprefix("ORDER_")
        title, template = STATUS_TEXT[status]
        reason = f" Reason: {order.status_reason}" if order.status_reason else ""
        message = template.format(store=order.store.store_name, number=number, reason=reason)
        _to_customer(order, NotificationType(event), title, message)
        if status == OrderStatus.CANCELLED and actor != Actor.STORE_OWNER and _owner_can_see(order):
            create_notification(
                order.store.owner_id,
                NotificationType.ORDER_CANCELLED,
                "Order cancelled",
                f"Order {number} was cancelled.{reason}",
                order=order,
            )


def _to_customer(order, notification_type, title, message):
    create_notification(order.customer_id, notification_type, title, message, order=order)


def _new_order_to_owner(order):
    create_notification(
        order.store.owner_id,
        NotificationType.ORDER_RECEIVED,
        "New order",
        f"New order {order.order_number} for {order.total_amount} TZS.",
        order=order,
    )


def _is_cash(order):
    return order.payments.filter(payment_method=PaymentMethod.CASH).exists()


def _owner_can_see(order):
    return order.payment_status == PaymentStatus.SUCCESS or _is_cash(order)


def notify_low_stock(store_owner_id, products):
    """products: (product, remaining) pairs that just dropped to or below their threshold."""
    try:
        for product, remaining in products:
            create_notification(
                store_owner_id,
                NotificationType.LOW_STOCK,
                "Low stock",
                f"{product.name} is down to {remaining} (alert at {product.low_stock_threshold}).",
            )
    except Exception:
        logger.exception("Could not send low stock notifications")


def crossed_low_stock(product, before, after):
    """True only when this change moves stock from above the threshold to at/below it."""
    return before > product.low_stock_threshold >= after
