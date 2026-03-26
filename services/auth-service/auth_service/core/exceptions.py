"""
auth_service/core/exceptions.py
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        payload = {
            "success": False,
            "error": {
                "code":    response.status_code,
                "message": _flatten_errors(response.data),
            },
        }
        response.data = payload
        return response

    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {"success": False, "error": {"code": 500, "message": "Internal server error"}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _flatten_errors(data):
    if isinstance(data, dict):
        msgs = []
        for key, val in data.items():
            if isinstance(val, list):
                msgs.append(f"{key}: {', '.join(str(v) for v in val)}")
            else:
                msgs.append(str(val))
        return " | ".join(msgs)
    if isinstance(data, list):
        return " | ".join(str(v) for v in data)
    return str(data)


class YanaAuthError(Exception):
    """Base auth error."""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code    = code
        super().__init__(message)


class InvalidOTPError(YanaAuthError):
    def __init__(self):
        super().__init__("Invalid or expired OTP", 401)


class RiderNotFoundError(YanaAuthError):
    def __init__(self):
        super().__init__("Rider not found", 404)


class AdminNotFoundError(YanaAuthError):
    def __init__(self):
        super().__init__("Admin user not found or inactive", 401)
