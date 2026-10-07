from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from accounts.managers import UserManager
from accounts.validators import validate_phone


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    CUSTOMER = "CUSTOMER", "Customer"
    STORE_OWNER = "STORE_OWNER", "Store owner"
    DRIVER = "DRIVER", "Driver"


class User(AbstractBaseUser, PermissionsMixin):
    """Single authentication table. Login identifier is phone."""

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True, validators=[validate_phone])
    email = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    role = models.CharField(max_length=32, choices=UserRole.choices)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.phone


class Customer(models.Model):
    """Profile for role CUSTOMER. The user id is the primary key."""

    # The profile is part of the user. Deleting the user removes the profile.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="customer_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Customer {self.user.phone}"


class StoreOwner(models.Model):
    """Profile for role STORE_OWNER. One owner may own many stores."""

    # The profile is part of the user. Deleting the user removes the profile.
    # Stores that still reference this profile block that delete (PROTECT).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="store_owner_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "store_owners"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Store owner {self.user.phone}"


class Address(models.Model):
    """Delivery address owned by a customer. At most one default per customer."""

    # Addresses belong to the customer profile, so they go away with it.
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_name = models.CharField(max_length=50)
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    area = models.CharField(max_length=80, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "addresses"
        ordering = ["-is_default", "address_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(is_default=True),
                name="uniq_default_address_per_customer",
            ),
        ]

    def __str__(self):
        return f"{self.address_name} ({self.city})"
