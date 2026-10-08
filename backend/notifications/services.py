import logging

from django.db import transaction

from notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


def create_notification(user_id, notification_type, title, message, order=None):
    """Store an in-app notification once the surrounding transaction commits.

    A rolled-back change therefore never notifies anyone.
    """
    order_id = order.pk if order is not None else None
    transaction.on_commit(
        lambda: Notification.objects.create(
            user_id=user_id,
            order_id=order_id,
            notification_type=notification_type,
            title=title,
            message=message,
        ),
        robust=True,
    )


def notify_if_became_low(product, before_stock, before_threshold):
    """Tell the store owner when a change takes a product from above its low-stock
    threshold to at or below it: once per crossing, from orders or the owner's edits.

    product must hold the new stock and threshold, and have its store loaded.
    """
    was_low = before_stock <= before_threshold
    is_low = product.stock_quantity <= product.low_stock_threshold
    if was_low or not is_low:
        return
    try:
        create_notification(
            product.store.owner_id,
            NotificationType.LOW_STOCK,
            "Low stock",
            f"{product.name} is down to {product.stock_quantity} "
            f"(alert at {product.low_stock_threshold}).",
        )
    except Exception:
        logger.exception("Could not send the low stock notification for %s", product.pk)


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return notification


def mark_all_read(user):
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)


def unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()
