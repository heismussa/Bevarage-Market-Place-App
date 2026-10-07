from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from catalog.models import ProductUnit
from payments.choices import PaymentStatus


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    PREPARING = "PREPARING", "Preparing"
    READY = "READY", "Ready"
    ASSIGNED = "ASSIGNED", "Assigned"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(models.Model):
    """Customer order.

    customer and store use PROTECT so order history cannot be removed by
    deleting the customer or the store. address uses SET_NULL because the
    address row may be deleted later; delivery_* snapshot columns stay.
    """

    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    delivery_address = models.CharField(max_length=255)
    delivery_phone = models.CharField(max_length=20)
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    order_status = models.CharField(
        max_length=32,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    payment_status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    notes = models.TextField(null=True, blank=True)
    status_reason = models.TextField(null=True, blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-ordered_at"]
        indexes = [
            models.Index(fields=["store", "order_status"], name="order_store_status_idx"),
            models.Index(
                fields=["customer", "ordered_at"],
                name="order_customer_ordered_idx",
            ),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    """Snapshot line on an order. Rows CASCADE with the order.

    product uses PROTECT so a product that appears in order history cannot
    be hard-deleted.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=100)
    unit = models.CharField(max_length=32, choices=ProductUnit.choices)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_items"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="order_item_qty_gt_0",
            ),
        ]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusHistory(models.Model):
    """Append-only status trail. Rows CASCADE with the order.

    changed_by uses SET_NULL. NULL means the system (for example a webhook).
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=32,
        choices=OrderStatus.choices,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=32, choices=OrderStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "order_status_history"
        ordering = ["changed_at"]
        verbose_name_plural = "order status history"
        indexes = [
            models.Index(fields=["order", "changed_at"], name="order_status_history_idx"),
        ]

    def __str__(self):
        return f"{self.order} -> {self.status}"
