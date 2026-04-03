import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        data = response.data
        if isinstance(data, dict):
            message = " | ".join(
                f"{key}: {', '.join(value) if isinstance(value, list) else value}"
                for key, value in data.items()
            )
        elif isinstance(data, list):
            message = " | ".join(str(item) for item in data)
        else:
            message = str(data)

        response.data = {
            "success": False,
            "error": {"code": response.status_code, "message": message},
        }
        return response

    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {
            "success": False,
            "error": {"code": 500, "message": "Internal server error"},
        },
        status=500,
    )


class MarketplaceError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class SlotFullError(MarketplaceError):
    pass


class SlotNotPublishedError(MarketplaceError):
    pass


class AlreadyAppliedError(MarketplaceError):
    pass


class AttendanceError(MarketplaceError):
    pass


class EarningsError(MarketplaceError):
    pass
