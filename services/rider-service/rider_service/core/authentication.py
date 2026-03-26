"""
rider_service/core/authentication.py

JWT authentication for the rider service.
Validates tokens signed by auth-service.
"""
import jwt
import logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Rider

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """Lightweight wrapper for admin JWT claims (no DB lookup needed)."""

    def __init__(self, payload: dict):
        self.id         = payload.get("user_id")
        self.role       = payload.get("role", "")
        self.token_type = payload.get("token_type", "admin")
        self._payload   = payload
        self.is_active  = True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def has_role(self, *roles):
        return self.role in roles


class JWTAuthentication(BaseAuthentication):
    """
    Validates Bearer JWT tokens issued by auth-service.
    - Admin tokens: returns AuthenticatedUser (no DB hit)
    - Rider tokens: returns Rider ORM object
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired.")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {e}")

        # Check blacklist
        jti = payload.get("jti")
        if jti:
            from django.core.cache import cache
            if cache.get(f"yana:blacklist:{jti}"):
                raise AuthenticationFailed("Token has been revoked.")

        token_type = payload.get("token_type", "admin")

        if token_type == "rider":
            user_id = payload.get("user_id")
            try:
                rider = Rider.objects.get(id=user_id, deleted_at__isnull=True)
                rider._jwt_payload = payload
                return rider, token
            except Rider.DoesNotExist:
                raise AuthenticationFailed("Rider not found.")

        elif token_type == "admin":
            user = AuthenticatedUser(payload)
            return user, token

        raise AuthenticationFailed("Unknown token type.")
