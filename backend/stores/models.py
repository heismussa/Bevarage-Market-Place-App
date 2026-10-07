from decimal import Decimal

from django.core.validators import FileExtensionValidator
from django.db import models


class StoreStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"


class Store(models.Model):
    """A store owned by a store-owner profile.

    owner uses PROTECT so the owner profile cannot be removed while a store
    still points at it.
    """

    owner = models.ForeignKey(
        "accounts.StoreOwner",
        on_delete=models.PROTECT,
        related_name="stores",
    )
    store_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    # ERD column logo_url is an ImageField named logo. The stored value is the file path.
    logo = models.ImageField(
        upload_to="stores/logos/",
        max_length=255,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
        ],
    )
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=80, null=True, blank=True)
    area = models.CharField(max_length=80, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100, null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=StoreStatus.choices,
        default=StoreStatus.CLOSED,
    )
    is_active = models.BooleanField(default=True)
    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stores"
        ordering = ["store_name"]
        indexes = [
            models.Index(fields=["city", "area"], name="store_city_area_idx"),
        ]

    def __str__(self):
        return self.store_name
