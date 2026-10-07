from django.db import models

from payments.choices import PaymentMethod, PaymentStatus


class Payment(models.Model):
    """A payment attempt. An order may have many (retries).

    order uses PROTECT. Payment rows are financial records, so deleting an
    order must not cascade-delete them. Cart items and order items are the
    children that CASCADE; payments are not.
    """

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=32, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    transaction_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    payer_phone = models.CharField(max_length=20, null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    gateway_response = models.JSONField(null=True, blank=True)
    payment_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["payment_status"], name="payment_status_idx"),
        ]

    def __str__(self):
        return self.transaction_reference or f"Payment {self.pk}"
