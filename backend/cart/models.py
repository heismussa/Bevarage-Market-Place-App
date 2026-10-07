from django.db import models
from django.db.models import Q


class Cart(models.Model):
    """One active cart per customer.

    customer uses CASCADE because the cart is owned by that profile.
    store stays nullable (an empty cart has no store) and uses PROTECT so a
    cart that has already chosen a store is not silently detached by deleting
    that store.
    """

    customer = models.OneToOneField(
        "accounts.Customer",
        on_delete=models.CASCADE,
        related_name="cart",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart {self.pk} ({self.customer})"


class CartItem(models.Model):
    """Line on a cart. Rows CASCADE with the cart.

    product uses PROTECT so a product that is still in a cart cannot be
    hard-deleted. Products are soft-deleted via deleted_at instead.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="uniq_cart_product",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="cart_item_qty_gt_0",
            ),
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity}"
