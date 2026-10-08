from django.db import transaction

from accounts.models import Address, Customer


def _lock_customer(customer):
    """Serialize address changes per customer so default handling cannot race."""
    Customer.objects.select_for_update().get(pk=customer.pk)


@transaction.atomic
def create_address(customer, data):
    _lock_customer(customer)
    is_first = not Address.objects.filter(customer=customer).exists()
    return Address.objects.create(customer=customer, is_default=is_first, **data)


@transaction.atomic
def update_address(address, data):
    _lock_customer(address.customer)
    address = Address.objects.get(pk=address.pk)
    for field, value in data.items():
        setattr(address, field, value)
    address.save()
    return address


@transaction.atomic
def set_default_address(address):
    _lock_customer(address.customer)
    Address.objects.filter(customer_id=address.customer_id, is_default=True).exclude(
        pk=address.pk
    ).update(is_default=False)
    Address.objects.filter(pk=address.pk).update(is_default=True)
    address.refresh_from_db()
    return address


@transaction.atomic
def delete_address(address):
    """Delete the address. If it was the default, promote the most recently created one."""
    _lock_customer(address.customer)
    customer_id = address.customer_id
    was_default = Address.objects.filter(pk=address.pk, is_default=True).exists()
    address.delete()
    if was_default:
        newest = (
            Address.objects.filter(customer_id=customer_id).order_by("-created_at", "-id").first()
        )
        if newest is not None:
            Address.objects.filter(pk=newest.pk).update(is_default=True)
