"""marketplace_service/core/authentication.py"""
import jwt, logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    def __init__(self, payload):
        self.id         = payload.get("user_id")
        self.role       = payload.get("role", "")
        self.token_type = payload.get("token_type", "admin")
        self.is_active  = True

    @property
    def is_authenticated(self): return True

    @property
    def is_anonymous(self): return False


class AuthenticatedRider:
    def __init__(self, rider_id):
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

        if payload.get("token_type") == "rider":
            return AuthenticatedRider(payload.get("user_id")), token
        return AuthenticatedUser(payload), token


# ── Permissions ───────────────────────────────────────────────

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser)

class IsRider(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedRider)

class IsRiderOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, (AuthenticatedUser, AuthenticatedRider))

class IsSalesOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN", "CITY_ADMIN", "SALES"}
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser) and request.user.role in self.ALLOWED

class IsOpsOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN", "CITY_ADMIN", "HUB_OPS"}
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser) and request.user.role in self.ALLOWED


# ── Exceptions ────────────────────────────────────────────────

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        d = response.data
        if isinstance(d, dict):
            msg = " | ".join(f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in d.items())
        elif isinstance(d, list):
            msg = " | ".join(str(e) for e in d)
        else:
            msg = str(d)
        response.data = {"success": False, "error": {"code": response.status_code, "message": msg}}
        return response
    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response({"success": False, "error": {"code": 500, "message": "Internal server error"}}, status=500)


class MarketplaceError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

class SlotFullError(MarketplaceError):      pass
class SlotNotPublishedError(MarketplaceError): pass
class AlreadyAppliedError(MarketplaceError):  pass
class AttendanceError(MarketplaceError):      pass
class EarningsError(MarketplaceError):        pass


# ── Pagination ────────────────────────────────────────────────

class StandardPagination(PageNumberPagination):
    page_size             = 20
    page_size_query_param = "page_size"
    max_page_size         = 100

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": {
                "results":     data,
                "count":       self.page.paginator.count,
                "page":        self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "next":        self.get_next_link(),
                "previous":    self.get_previous_link(),
            },
        })
