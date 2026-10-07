from django.contrib.auth import get_user_model
from django.db.models.signals import post_save


def create_profile_for_role(sender, instance, created, **kwargs):
    """Create the ERD profile row for a new customer or store owner.

    ADMIN has no profile table. DRIVER is planned for later and has no model yet.
    """
    if not created:
        return

    from accounts.models import Customer, StoreOwner, UserRole

    if instance.role == UserRole.CUSTOMER:
        Customer.objects.get_or_create(user=instance)
    elif instance.role == UserRole.STORE_OWNER:
        StoreOwner.objects.get_or_create(user=instance)


def connect_profile_signal():
    post_save.connect(
        create_profile_for_role,
        sender=get_user_model(),
        dispatch_uid="accounts.create_profile_for_role",
    )
