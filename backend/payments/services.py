"""Payment rules.

- SUCCESS is set only by a verified webhook, or for cash when the store completes the order.
- Webhooks are idempotent: a payment that already reached SUCCESS or FAILED is not changed.
- Money that arrives but cannot be kept (wrong amount, second payment, cancelled order) is
  flagged with a REFUND_REQUIRED note on the order history. Refunds are handled manually.
"""

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from core.errors import ApiError, ErrorCode
from orders import events
from orders.models import Order, OrderStatus, OrderStatusHistory
from payments.choices import PaymentMethod, PaymentStatus
from payments.models import Payment
from payments.providers import get_provider, provider_for_method
from payments.providers.base import InvalidWebhookPayload

REFUND_REQUIRED = "REFUND_REQUIRED"
PAYMENT_SUCCESS = events.PAYMENT_SUCCESS
PAYMENT_FAILED = events.PAYMENT_FAILED
FINAL_PAYMENT_STATUSES = frozenset({PaymentStatus.SUCCESS, PaymentStatus.FAILED})


def _conflict(code, message, details=None):
    return ApiError(code, message, status_code=status.HTTP_409_CONFLICT, details=details)


def latest_payment(order):
    return order.payments.order_by("-created_at", "-id").first()


def cash_order_condition():
    """Q matching orders paid in cash. All attempts of an order use the same method."""
    return Exists(Payment.objects.filter(order=OuterRef("pk"), payment_method=PaymentMethod.CASH))


def visible_to_store_owner(queryset):
    """Cash orders are visible at once; other orders only after payment SUCCESS."""
    return queryset.filter(Q(cash_order_condition()) | Q(payment_status=PaymentStatus.SUCCESS))


def add_refund_note(order, message):
    """Append a REFUND_REQUIRED entry without changing the order status."""
    OrderStatusHistory.objects.create(
        order=order,
        from_status=order.order_status,
        status=order.order_status,
        changed_by=None,
        notes=f"{REFUND_REQUIRED}: {message}",
    )


# --- Customer-initiated payment -------------------------------------------------------


@transaction.atomic
def initiate_payment(order, payer_phone=None):
    """Start the first payment attempt or retry after FAILED. Never sets SUCCESS."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    current = latest_payment(order)
    method = current.payment_method if current else None

    if order.order_status != OrderStatus.PENDING:
        raise _conflict(
            ErrorCode.PAYMENT_NOT_ALLOWED,
            f"An order that is {order.order_status} cannot be paid.",
            {"order_status": order.order_status},
        )
    if order.payment_status == PaymentStatus.SUCCESS:
        raise _conflict(ErrorCode.PAYMENT_NOT_ALLOWED, "This order is already paid.")
    if current is None:
        raise _conflict(ErrorCode.PAYMENT_NOT_ALLOWED, "This order has no payment method.")
    if method == PaymentMethod.CASH:
        raise _conflict(
            ErrorCode.PAYMENT_NOT_ALLOWED,
            "Cash orders are paid on delivery.",
            {"payment_method": method},
        )
    if current.payment_status == PaymentStatus.PROCESSING:
        raise _conflict(
            ErrorCode.PAYMENT_IN_PROGRESS,
            "A payment prompt is already waiting for approval.",
            {"payment_id": current.pk},
        )

    provider = provider_for_method(method)
    if provider is None:
        raise _conflict(
            ErrorCode.PAYMENT_NOT_ALLOWED,
            "This payment method is not available.",
            {"payment_method": method},
        )

    if current.payment_status == PaymentStatus.PENDING:
        payment = current
        if payer_phone:
            payment.payer_phone = payer_phone
    else:
        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            currency=current.currency,
            payment_method=method,
            payment_status=PaymentStatus.PENDING,
            payer_phone=payer_phone or current.payer_phone,
        )

    result = provider.initiate(payment)
    payment.payment_status = result.status
    payment.transaction_reference = result.transaction_reference
    payment.save()
    order.payment_status = result.status
    order.save(update_fields=["payment_status", "updated_at"])
    return payment, result


# --- Webhooks -------------------------------------------------------------------------


def _mirror_on_order(order, payment_status):
    """order.payment_status mirrors the latest payment, but a paid order stays paid."""
    if order.payment_status != PaymentStatus.SUCCESS:
        order.payment_status = payment_status
        order.save(update_fields=["payment_status", "updated_at"])


def handle_webhook(provider_name, body, headers):
    """Verify, parse and apply a provider webhook. Returns the Payment."""
    provider = get_provider(provider_name)
    if provider is None:
        raise NotFound("Unknown payment provider.")
    if not provider.verify_webhook(body, headers):
        raise ApiError(
            ErrorCode.INVALID_SIGNATURE,
            "Webhook signature is missing or invalid.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        event = provider.parse_event(body)
    except InvalidWebhookPayload as exc:
        raise ValidationError({"body": [str(exc)]}) from exc
    return _apply_event(event)


@transaction.atomic
def _apply_event(event):
    payment = (
        Payment.objects.select_for_update()
        .filter(transaction_reference=event.transaction_reference)
        .first()
    )
    if payment is None:
        raise NotFound("Unknown transaction reference.")
    if payment.payment_status in FINAL_PAYMENT_STATUSES:
        return payment

    order = Order.objects.select_for_update().get(pk=payment.order_id)
    payment.gateway_response = event.payload

    if not event.succeeded:
        payment.payment_status = PaymentStatus.FAILED
        payment.save()
        _mirror_on_order(order, PaymentStatus.FAILED)
        _notify(order, PAYMENT_FAILED)
        return payment

    expected = order.total_amount
    if event.amount != expected or event.currency != payment.currency:
        payment.payment_status = PaymentStatus.FAILED
        payment.save()
        _mirror_on_order(order, PaymentStatus.FAILED)
        add_refund_note(
            order,
            f"received {event.amount} {event.currency} on {payment.transaction_reference} "
            f"but the order total is {expected} {payment.currency}.",
        )
        _notify(order, PAYMENT_FAILED)
        return payment

    already_paid = order.payment_status == PaymentStatus.SUCCESS
    payment.payment_status = PaymentStatus.SUCCESS
    payment.payment_time = timezone.now()
    payment.save()

    if already_paid:
        add_refund_note(
            order, f"second payment {payment.transaction_reference} for an order already paid."
        )
        return payment

    order.payment_status = PaymentStatus.SUCCESS
    order.save(update_fields=["payment_status", "updated_at"])
    if order.order_status in (OrderStatus.CANCELLED, OrderStatus.REJECTED):
        add_refund_note(
            order,
            f"payment {payment.transaction_reference} arrived after the order was "
            f"{order.order_status}.",
        )
    _notify(order, PAYMENT_SUCCESS)
    return payment


def _notify(order, event):
    transaction.on_commit(lambda: events.notify_order_event(order, event))


# --- Hooks used by order transitions --------------------------------------------------


def collect_cash_on_completion(order):
    """Mark a cash order paid when the store completes it. Call inside the transition."""
    payment = latest_payment(order)
    if payment is None or payment.payment_method != PaymentMethod.CASH:
        return False
    if payment.payment_status != PaymentStatus.SUCCESS:
        payment.payment_status = PaymentStatus.SUCCESS
        payment.payment_time = timezone.now()
        payment.save(update_fields=["payment_status", "payment_time", "updated_at"])
    order.payment_status = PaymentStatus.SUCCESS
    return True


def cancel_unstarted_payments(order):
    """On reject/cancel: attempts never sent to a provider are cancelled. Prompts already
    sent (PROCESSING) are left alone; if they succeed later the webhook flags a refund."""
    Payment.objects.filter(order=order, payment_status=PaymentStatus.PENDING).update(
        payment_status=PaymentStatus.CANCELLED, updated_at=timezone.now()
    )
    if order.payment_status == PaymentStatus.PENDING:
        order.payment_status = PaymentStatus.CANCELLED
