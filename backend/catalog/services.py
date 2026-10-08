from django.db import IntegrityError, transaction
from django.db.models import Case, F, Q, Value, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from catalog.models import AvailabilityStatus, Product

DUPLICATE_NAME_MESSAGE = "This store already has a product with this name."


def compute_availability(current_status, stock_quantity):
    """Availability after a stock change.

    - stock 0 -> OUT_OF_STOCK
    - stock > 0 and previously OUT_OF_STOCK -> AVAILABLE
    - otherwise unchanged (UNAVAILABLE is only ever set by the owner)
    """
    if stock_quantity <= 0:
        return AvailabilityStatus.OUT_OF_STOCK
    if current_status == AvailabilityStatus.OUT_OF_STOCK:
        return AvailabilityStatus.AVAILABLE
    return current_status


def sync_availability(queryset):
    """Apply compute_availability in one UPDATE. For bulk stock changes made with F()."""
    return queryset.update(
        availability_status=Case(
            When(stock_quantity__lte=0, then=Value(AvailabilityStatus.OUT_OF_STOCK)),
            When(
                Q(availability_status=AvailabilityStatus.OUT_OF_STOCK) & Q(stock_quantity__gt=0),
                then=Value(AvailabilityStatus.AVAILABLE),
            ),
            default=F("availability_status"),
        )
    )


def _save(product, **save_kwargs):
    try:
        with transaction.atomic():
            product.save(**save_kwargs)
    except IntegrityError as exc:
        if "uniq_active_product_per_store" in str(exc):
            raise ValidationError({"name": [DUPLICATE_NAME_MESSAGE]}) from exc
        raise
    return product


@transaction.atomic
def create_product(store, data):
    product = Product(store=store, **data)
    product.availability_status = compute_availability(
        product.availability_status, product.stock_quantity
    )
    return _save(product)


@transaction.atomic
def update_product(product, data):
    product = Product.objects.select_for_update().get(pk=product.pk)
    for field, value in data.items():
        setattr(product, field, value)
    product.availability_status = compute_availability(
        product.availability_status, product.stock_quantity
    )
    return _save(product)


@transaction.atomic
def set_stock(product, stock_quantity):
    product = Product.objects.select_for_update().get(pk=product.pk)
    product.stock_quantity = stock_quantity
    product.availability_status = compute_availability(product.availability_status, stock_quantity)
    return _save(product, update_fields=["stock_quantity", "availability_status", "updated_at"])


@transaction.atomic
def soft_delete_product(product):
    product = Product.objects.select_for_update().get(pk=product.pk)
    if product.deleted_at is None:
        product.deleted_at = timezone.now()
        product.save(update_fields=["deleted_at", "updated_at"])
    return product
