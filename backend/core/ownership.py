"""Object-level ownership helpers.

Rows the user does not own are filtered out of the queryset, so lookups for
them raise 404 rather than 403. That way the API does not reveal that the
object exists.
"""

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


class OwnerField:
    """Lookup paths from a model to the owning User."""

    CUSTOMER = "customer__user"
    STORE_OWNER = "owner__user"
    STORE_OF_OBJECT = "store__owner__user"
    USER = "user"


def scope_to_owner(queryset, owner_field, user):
    if not owner_field:
        raise ImproperlyConfigured("owner_field is required to scope a queryset.")
    if user is None or not user.is_authenticated:
        return queryset.none()
    return queryset.filter(**{owner_field: user})


def get_owned_or_404(queryset, owner_field, user, **lookup):
    return get_object_or_404(scope_to_owner(queryset, owner_field, user), **lookup)


class OwnerScopedQuerysetMixin:
    """Restrict a generic view's queryset to rows owned by request.user.

    Set owner_field to one of the OwnerField paths.
    """

    owner_field = None

    def get_queryset(self):
        return scope_to_owner(super().get_queryset(), self.owner_field, self.request.user)


def get_customer_profile(user):
    try:
        return user.customer_profile
    except ObjectDoesNotExist as exc:
        raise PermissionDenied("A customer profile is required.") from exc


def get_store_owner_profile(user):
    try:
        return user.store_owner_profile
    except ObjectDoesNotExist as exc:
        raise PermissionDenied("A store owner profile is required.") from exc
