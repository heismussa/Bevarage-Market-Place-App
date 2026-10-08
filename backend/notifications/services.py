from django.db import transaction

from notifications.models import Notification


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


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return notification


def mark_all_read(user):
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)


def unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()
