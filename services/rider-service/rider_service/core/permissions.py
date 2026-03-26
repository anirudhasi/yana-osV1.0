"""
rider_service/core/permissions.py
"""
from rest_framework.permissions import BasePermission
from .models import Rider
from .authentication import AuthenticatedUser


class IsRider(BasePermission):
    """Allows only authenticated riders."""
    message = "Rider authentication required."

    def has_permission(self, request, view):
        return isinstance(request.user, Rider) and request.user.deleted_at is None


class IsAdminUser(BasePermission):
    """Allows any admin (any role)."""
    message = "Admin authentication required."

    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser)


class IsOpsOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN", "CITY_ADMIN", "HUB_OPS"}
    message = "Ops-level access required."

    def has_permission(self, request, view):
        return (
            isinstance(request.user, AuthenticatedUser)
            and request.user.role in self.ALLOWED
        )


class IsSuperAdmin(BasePermission):
    message = "Super admin access required."

    def has_permission(self, request, view):
        return (
            isinstance(request.user, AuthenticatedUser)
            and request.user.role == "SUPER_ADMIN"
        )


class IsRiderOrAdmin(BasePermission):
    """Allows rider (own data) or any admin."""

    def has_permission(self, request, view):
        return isinstance(request.user, (Rider, AuthenticatedUser))

    def has_object_permission(self, request, view, obj):
        if isinstance(request.user, AuthenticatedUser):
            return True
        if isinstance(request.user, Rider):
            # Rider can only access their own record
            if hasattr(obj, "rider"):
                return obj.rider_id == request.user.id
            if isinstance(obj, Rider):
                return str(obj.id) == str(request.user.id)
        return False
