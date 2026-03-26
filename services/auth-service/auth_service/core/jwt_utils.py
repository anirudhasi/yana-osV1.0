"""
auth_service/core/jwt_utils.py

JWT token generation and validation helpers.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from django.conf import settings


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def generate_access_token(user_id: str, role: str, token_type: str = "admin") -> str:
    """Generate a short-lived access token."""
    payload = {
        "user_id":    str(user_id),
        "role":       role,
        "token_type": token_type,
        "type":       "access",
        "iat":        _now(),
        "exp":        _now() + timedelta(minutes=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].seconds // 60),
        "jti":        str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SIMPLE_JWT["SIGNING_KEY"], algorithm="HS256")


def generate_refresh_token(user_id: str, role: str, token_type: str = "admin") -> str:
    """Generate a long-lived refresh token."""
    payload = {
        "user_id":    str(user_id),
        "role":       role,
        "token_type": token_type,
        "type":       "refresh",
        "iat":        _now(),
        "exp":        _now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
        "jti":        str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SIMPLE_JWT["SIGNING_KEY"], algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload or None."""
    try:
        return jwt.decode(token, settings.SIMPLE_JWT["SIGNING_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def build_token_response(user_id: str, role: str, token_type: str = "admin") -> dict:
    return {
        "access_token":  generate_access_token(user_id, role, token_type),
        "refresh_token": generate_refresh_token(user_id, role, token_type),
        "token_type":    "Bearer",
        "expires_in":    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].seconds,
    }
