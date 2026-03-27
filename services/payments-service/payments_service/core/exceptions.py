"""payments_service/core/exceptions.py"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import logging

logger = logging.getLogger(__name__)


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


class PaymentsError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InsufficientBalanceError(PaymentsError): pass
class WalletLockedError(PaymentsError):        pass
class DuplicateTransactionError(PaymentsError): pass
class GatewayError(PaymentsError):             pass
class RentScheduleError(PaymentsError):        pass


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
