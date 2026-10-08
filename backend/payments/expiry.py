from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderStatus
from orders.services import transition_order
from orders.state_machine import Action
from payments.choices import PaymentStatus
from payments.services import cash_order_condition


def expiry_cutoff():
    return timezone.now() - timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES)


def expiry_reason():
    return f"Payment was not received within {settings.PAYMENT_TIMEOUT_MINUTES} minutes."


def expirable_orders(cutoff):
    """Unpaid, non-cash, still PENDING and older than the cutoff."""
    return (
        Order.objects.filter(order_status=OrderStatus.PENDING, ordered_at__lt=cutoff)
        .exclude(payment_status=PaymentStatus.SUCCESS)
        .filter(~cash_order_condition())
    )


@transaction.atomic
def expire_order(order_id, cutoff):
    """Cancel one order if it still qualifies once locked. Returns True if cancelled."""
    order = expirable_orders(cutoff).select_for_update().filter(pk=order_id).first()
    if order is None:
        return False
    transition_order(order, Action.CANCEL, None, expiry_reason())
    return True


def expire_unpaid_orders():
    """Cancel every expired unpaid order, each in its own transaction. Safe to re-run."""
    cutoff = expiry_cutoff()
    order_ids = list(expirable_orders(cutoff).values_list("pk", flat=True))
    return sum(expire_order(order_id, cutoff) for order_id in order_ids)
