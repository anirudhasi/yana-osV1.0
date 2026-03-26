"""
auth_service/core/permissions.py

Custom DRF authentication + permission classes.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from .jwt_utils import decode_token
from .models import AdminUser, Rider


class JWTAuthentication(BaseAuthentication):
    """
    Authenticates requests using the Bearer JWT token.
    Sets request.user to AdminUser or a RiderProxy.
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if not payload:
            raise AuthenticationFailed("Token is invalid or expired.")

        token_type = payload.get("token_type", "admin")
        user_id    = payload.get("user_id")

        if token_type == "admin":
            try:
                user = AdminUser.objects.get(id=user_id, is_active=True, deleted_at__isnull=True)
            except AdminUser.DoesNotExist:
                raise AuthenticationFailed("Admin account not found or deactivated.")
            user._jwt_payload = payload
            return user, token

        elif token_type == "rider":
            try:
                user = Rider.objects.get(id=user_id, deleted_at__isnull=True)
            except Rider.DoesNotExist:
                raise AuthenticationFailed("Rider account not found.")
            user._jwt_payload = payload
            user.role = "RIDER"
            return user, token

        raise AuthenticationFailed("Unknown token type.")


class IsAdminUser(BasePermission):
    """Allows only admin users (any role)."""
    def has_permission(self, request, view):
        return (
            request.user is not None
            and isinstance(request.user, AdminUser)
            and request.user.is_active
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            IsAdminUser().has_permission(request, view)
            and request.user.role == "SUPER_ADMIN"
        )


class IsOpsOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN", "CITY_ADMIN", "HUB_OPS"}

    def has_permission(self, request, view):
        return (
            IsAdminUser().has_permission(request, view)
            and request.user.role in self.ALLOWED
        )


class IsRider(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user is not None
            and isinstance(request.user, Rider)
        )
