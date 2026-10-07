from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q


class CategoryStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class ProductUnit(models.TextChoices):
    BOTTLE = "BOTTLE", "Bottle"
    CAN = "CAN", "Can"
    CRATE = "CRATE", "Crate"
    CARTON = "CARTON", "Carton"
    PACK = "PACK", "Pack"


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    OUT_OF_STOCK = "OUT_OF_STOCK", "Out of stock"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=CategoryStatus.choices,
        default=CategoryStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """A store-owned product. Soft-deleted rows keep deleted_at set.

    store and category use PROTECT so catalog rows are not removed by deleting
    the store or category they belong to. Order items also PROTECT the product.
    """

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(
        upload_to="products/",
        max_length=255,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
        ],
    )
    unit = models.CharField(max_length=32, choices=ProductUnit.choices)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    availability_status = models.CharField(
        max_length=32,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="product_price_gt_0",
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="product_stock_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(low_stock_threshold__gte=0),
                name="product_low_stock_gte_0",
            ),
            models.UniqueConstraint(
                fields=["store", "name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_active_product_per_store",
            ),
        ]
        indexes = [
            models.Index(fields=["availability_status"], name="product_availability_idx"),
        ]

    def __str__(self):
        return self.name
