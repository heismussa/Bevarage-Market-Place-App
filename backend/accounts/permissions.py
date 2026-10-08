from rest_framework.permissions import BasePermission

from accounts.models import UserRole


class IsCustomer(BasePermission):
    message = "This action is limited to customers."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == UserRole.CUSTOMER
        )


class IsStoreOwner(BasePermission):
    message = "This action is limited to store owners."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == UserRole.STORE_OWNER
        )


class IsAdminRole(BasePermission):
    message = "This action is limited to administrators."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == UserRole.ADMIN
        )
