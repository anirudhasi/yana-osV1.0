"""payments_service/core/authentication.py"""
import jwt, logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    def __init__(self, payload):
        self.id         = payload.get("user_id")
        self.role       = payload.get("role", "")
        self.token_type = payload.get("token_type", "admin")
        self._payload   = payload
        self.is_active  = True

    @property
    def is_authenticated(self): return True

    @property
    def is_anonymous(self): return False


class AuthenticatedRider:
    def __init__(self, rider_id: str):
        self.id   = rider_id
        self.role = "RIDER"
        self.is_active = True

    @property
    def is_authenticated(self): return True

    @property
    def is_anonymous(self): return False


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired.")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {e}")

        from django.core.cache import cache
        if cache.get(f"yana:blacklist:{payload.get('jti')}"):
            raise AuthenticationFailed("Token revoked.")

        token_type = payload.get("token_type", "admin")
        user_id    = payload.get("user_id")

        if token_type == "rider":
            return AuthenticatedRider(user_id), token
        return AuthenticatedUser(payload), token


class IsAdminUser(BasePermission):
    message = "Admin authentication required."
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser)


class IsRider(BasePermission):
    message = "Rider authentication required."
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedRider)


class IsRiderOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, (AuthenticatedUser, AuthenticatedRider))


class IsFinanceOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN", "CITY_ADMIN", "SALES"}
    message = "Finance-level access required."
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser) and request.user.role in self.ALLOWED
