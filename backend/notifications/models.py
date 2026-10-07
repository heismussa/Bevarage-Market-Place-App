from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    ORDER_RECEIVED = "ORDER_RECEIVED", "Order received"
    ORDER_ACCEPTED = "ORDER_ACCEPTED", "Order accepted"
    ORDER_REJECTED = "ORDER_REJECTED", "Order rejected"
    ORDER_PREPARING = "ORDER_PREPARING", "Order preparing"
    ORDER_READY = "ORDER_READY", "Order ready"
    ORDER_COMPLETED = "ORDER_COMPLETED", "Order completed"
    ORDER_CANCELLED = "ORDER_CANCELLED", "Order cancelled"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED", "Driver assigned"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS", "Payment success"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
    LOW_STOCK = "LOW_STOCK", "Low stock"


class Notification(models.Model):
    """A message for one user.

    user uses CASCADE because the notification belongs to that user.
    order uses SET_NULL because the link is optional and the message can
    remain if the order row is removed.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"], name="notification_user_read_idx"),
        ]

    def __str__(self):
        return self.title
