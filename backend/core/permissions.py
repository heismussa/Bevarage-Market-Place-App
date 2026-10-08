from rest_framework.permissions import BasePermission


class DenyAll(BasePermission):
    """Project default. Every view must declare the permissions it needs."""

    def has_permission(self, request, view):
        return False
