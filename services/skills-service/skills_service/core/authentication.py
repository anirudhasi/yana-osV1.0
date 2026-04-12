"""
skills_service/core/authentication.py — JWT auth + permissions + pagination
"""
import jwt, logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class AuthenticatedUser:
    def __init__(self, payload):
        self.id = payload.get("user_id"); self.role = payload.get("role","")
        self.token_type = payload.get("token_type","admin"); self.is_active = True
    @property
    def is_authenticated(self): return True
    @property
    def is_anonymous(self): return False

class AuthenticatedRider:
    def __init__(self, rider_id):
        self.id = rider_id; self.role = "RIDER"; self.is_active = True
    @property
    def is_authenticated(self): return True
    @property
    def is_anonymous(self): return False

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        h = request.META.get("HTTP_AUTHORIZATION","")
        if not h.startswith("Bearer "): return None
        token = h.split(" ",1)[1].strip()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError: raise AuthenticationFailed("Token expired.")
        except jwt.InvalidTokenError as e: raise AuthenticationFailed(f"Invalid: {e}")
        from django.core.cache import cache
        if cache.get(f"yana:blacklist:{payload.get('jti')}"): raise AuthenticationFailed("Revoked.")
        if payload.get("token_type") == "rider": return AuthenticatedRider(payload.get("user_id")), token
        return AuthenticatedUser(payload), token

class IsAdminUser(BasePermission):
    def has_permission(self, request, view): return isinstance(request.user, AuthenticatedUser)
class IsRider(BasePermission):
    def has_permission(self, request, view): return isinstance(request.user, AuthenticatedRider)
class IsRiderOrAdmin(BasePermission):
    def has_permission(self, request, view): return isinstance(request.user, (AuthenticatedUser, AuthenticatedRider))
class IsOpsOrAbove(BasePermission):
    ALLOWED = {"SUPER_ADMIN","CITY_ADMIN","HUB_OPS"}
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser) and request.user.role in self.ALLOWED
class IsSupportAgent(BasePermission):
    ALLOWED = {"SUPER_ADMIN","CITY_ADMIN","SUPPORT_AGENT","HUB_OPS"}
    def has_permission(self, request, view):
        return isinstance(request.user, AuthenticatedUser) and request.user.role in self.ALLOWED

def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is not None:
        d = response.data
        msg = " | ".join(f"{k}: {', '.join(v) if isinstance(v,list) else v}" for k,v in d.items()) if isinstance(d,dict) else str(d)
        response.data = {"success": False, "error": {"code": response.status_code, "message": msg}}
        return response
    logger.exception("Unhandled in %s", context.get("view"))
    return Response({"success":False,"error":{"code":500,"message":"Internal server error"}},status=500)

class ServiceError(Exception):
    def __init__(self, message): self.message = message; super().__init__(message)

class StandardPagination(PageNumberPagination):
    page_size = 20; page_size_query_param = "page_size"; max_page_size = 100
    def get_paginated_response(self, data):
        return Response({"success":True,"data":{"results":data,"count":self.page.paginator.count,
            "page":self.page.number,"total_pages":self.page.paginator.num_pages,
            "next":self.get_next_link(),"previous":self.get_previous_link()}})
