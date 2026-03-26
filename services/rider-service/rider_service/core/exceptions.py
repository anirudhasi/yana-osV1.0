"""
rider_service/core/exceptions.py
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        if isinstance(errors, dict):
            msg = " | ".join(
                f"{k}: {', '.join(v) if isinstance(v, list) else v}"
                for k, v in errors.items()
            )
        elif isinstance(errors, list):
            msg = " | ".join(str(e) for e in errors)
        else:
            msg = str(errors)

        response.data = {
            "success": False,
            "error": {"code": response.status_code, "message": msg},
        }
        return response

    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {"success": False, "error": {"code": 500, "message": "Internal server error"}},
        status=500,
    )


# ── Custom error classes ──────────────────────────────────────

class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class KYCTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str):
        msg = f"Cannot transition KYC from '{from_status}' to '{to_status}'"
        super().__init__(msg)
        self.message = msg


class RiderStatusTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str):
        msg = f"Cannot transition rider status from '{from_status}' to '{to_status}'"
        super().__init__(msg)
        self.message = msg


class StorageError(Exception):
    pass
