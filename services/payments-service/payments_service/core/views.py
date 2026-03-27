"""
payments_service/core/views.py

Wallet & Payments APIs:
  GET    /payments/wallets/{rider_id}/            Wallet summary
  GET    /payments/wallets/{rider_id}/ledger/     Full ledger history
  POST   /payments/wallets/{rider_id}/topup/      Initiate Razorpay top-up
  POST   /payments/wallets/{rider_id}/topup/confirm/ Confirm top-up after payment
  POST   /payments/wallets/{rider_id}/adjust/     Admin manual adjustment
  POST   /payments/wallets/{rider_id}/incentive/  Credit incentive
  POST   /payments/wallets/{rider_id}/upi-mandate/ Setup UPI AutoPay
  DELETE /payments/wallets/{rider_id}/upi-mandate/ Revoke UPI mandate
  GET    /payments/rent/{rider_id}/schedule/      Rent schedule
  GET    /payments/rent/{rider_id}/overdue/       Overdue rents
  POST   /payments/rent/schedule/create/          Create schedule (internal)
  GET    /payments/transactions/{rider_id}/       Transaction history
  POST   /payments/webhooks/razorpay/             Razorpay webhook receiver
  GET    /payments/admin/summary/                 Platform-wide summary
"""
import hashlib
import hmac
import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import RiderWallet, WalletLedger, PaymentTransaction, RentSchedule, UPIMandate
from .serializers import (
    WalletSerializer, LedgerEntrySerializer, TransactionSerializer,
    RentScheduleSerializer, UPIMandateSerializer,
    TopUpInitiateSerializer, TopUpConfirmSerializer,
    AdminAdjustmentSerializer, IncentiveCreditSerializer,
    UPISetupSerializer, RentScheduleCreateSerializer, WalletSummarySerializer,
)
from .services import (
    ensure_wallet, initiate_topup, confirm_topup,
    credit_incentive, admin_adjustment,
    setup_upi_autopay, revoke_upi_autopay,
    create_rent_schedule, handle_razorpay_webhook,
)
from .ledger import get_wallet_summary
from .authentication import JWTAuthentication, IsAdminUser, IsRider, IsRiderOrAdmin, IsFinanceOrAbove
from .exceptions import (
    InsufficientBalanceError, GatewayError, RentScheduleError, StandardPagination
)

logger = logging.getLogger(__name__)


def ok(data, code=200):
    return Response({"success": True, "data": data}, status=code)

def err(message, code=400):
    return Response({"success": False, "error": {"message": message, "code": code}}, status=code)

def _rider_id_from_request(request, url_rider_id: str) -> str:
    """Allow riders to access only their own data; admins can access any."""
    from .authentication import AuthenticatedRider
    if isinstance(request.user, AuthenticatedRider):
        if str(request.user.id) != str(url_rider_id):
            return None   # Forbidden
    return str(url_rider_id)


# ─── Wallet ───────────────────────────────────────────────────

class WalletSummaryView(APIView):
    """GET /payments/wallets/{rider_id}/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)
        ensure_wallet(rid)
        summary = get_wallet_summary(rid)
        return ok(summary)


class WalletLedgerView(APIView):
    """GET /payments/wallets/{rider_id}/ledger/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        qs = WalletLedger.objects.filter(rider_id=rid).order_by("-created_at")

        # Filters
        ptype = request.query_params.get("payment_type")
        direction = request.query_params.get("direction")
        from_date = request.query_params.get("from_date")
        to_date   = request.query_params.get("to_date")

        if ptype:
            qs = qs.filter(payment_type=ptype)
        if direction:
            qs = qs.filter(direction=direction.upper())
        if from_date:
            qs = qs.filter(accounting_date__gte=from_date)
        if to_date:
            qs = qs.filter(accounting_date__lte=to_date)

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(LedgerEntrySerializer(page, many=True).data)


# ─── Top-up ───────────────────────────────────────────────────

class TopUpInitiateView(APIView):
    """POST /payments/wallets/{rider_id}/topup/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def post(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        s = TopUpInitiateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            result = initiate_topup(rid, s.validated_data["amount"])
            return ok(result, 201)
        except GatewayError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("Top-up initiation failed")
            return err(str(e), 500)


class TopUpConfirmView(APIView):
    """POST /payments/wallets/{rider_id}/topup/confirm/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def post(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        s = TopUpConfirmSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            entry = confirm_topup(
                rider_id            = rid,
                razorpay_order_id   = s.validated_data["razorpay_order_id"],
                razorpay_payment_id = s.validated_data["razorpay_payment_id"],
                razorpay_signature  = s.validated_data["razorpay_signature"],
            )
            return ok({
                "message":      "Wallet topped up successfully.",
                "ledger_entry": LedgerEntrySerializer(entry).data,
                "new_balance":  float(entry.balance_after),
            })
        except GatewayError as e:
            return err(e.message, 422)
        except Exception as e:
            logger.exception("Top-up confirmation failed")
            return err(str(e), 500)


# ─── Admin Adjustment ─────────────────────────────────────────

class AdminAdjustmentView(APIView):
    """POST /payments/wallets/{rider_id}/adjust/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsFinanceOrAbove]

    def post(self, request, rider_id):
        s = AdminAdjustmentSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            ensure_wallet(str(rider_id))
            entry = admin_adjustment(
                rider_id    = str(rider_id),
                amount      = s.validated_data["amount"],
                direction   = s.validated_data["direction"],
                description = s.validated_data["description"],
                admin_id    = str(request.user.id),
            )
            return ok({
                "message":      "Adjustment applied.",
                "ledger_entry": LedgerEntrySerializer(entry).data,
                "new_balance":  float(entry.balance_after),
            })
        except Exception as e:
            logger.exception("Adjustment failed")
            return err(str(e), 500)


# ─── Incentive ────────────────────────────────────────────────

class IncentiveCreditView(APIView):
    """POST /payments/wallets/{rider_id}/incentive/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsFinanceOrAbove]

    def post(self, request, rider_id):
        s = IncentiveCreditSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            ensure_wallet(str(rider_id))
            entry = credit_incentive(
                rider_id       = str(rider_id),
                amount         = s.validated_data["amount"],
                description    = s.validated_data["description"],
                reference_id   = str(s.validated_data["reference_id"]) if s.validated_data.get("reference_id") else None,
                reference_type = s.validated_data["reference_type"],
            )
            return ok({
                "message":      "Incentive credited.",
                "ledger_entry": LedgerEntrySerializer(entry).data,
                "new_balance":  float(entry.balance_after),
            })
        except Exception as e:
            logger.exception("Incentive credit failed")
            return err(str(e), 500)


# ─── UPI AutoPay ──────────────────────────────────────────────

class UPIMandateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)
        try:
            mandate = UPIMandate.objects.get(rider_id=rid)
            return ok(UPIMandateSerializer(mandate).data)
        except UPIMandate.DoesNotExist:
            return err("No UPI mandate found.", 404)

    def post(self, request, rider_id):
        """POST /payments/wallets/{rider_id}/upi-mandate/ — Setup mandate"""
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        s = UPISetupSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            mandate = setup_upi_autopay(
                rider_id    = rid,
                upi_id      = s.validated_data["upi_id"],
                rider_name  = s.validated_data["rider_name"],
                rider_phone = s.validated_data["rider_phone"],
                max_amount  = s.validated_data["max_amount"],
            )
            return ok(UPIMandateSerializer(mandate).data, 201)
        except Exception as e:
            return err(str(e), 500)

    def delete(self, request, rider_id):
        """DELETE /payments/wallets/{rider_id}/upi-mandate/ — Revoke"""
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)
        try:
            mandate = revoke_upi_autopay(rid)
            return ok({"message": "UPI mandate revoked.", "revoked_at": mandate.revoked_at})
        except UPIMandate.DoesNotExist:
            return err("No mandate found.", 404)


# ─── Rent Schedule ────────────────────────────────────────────

class RentScheduleView(APIView):
    """GET /payments/rent/{rider_id}/schedule/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        qs = RentSchedule.objects.filter(rider_id=rid).order_by("due_date")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(RentScheduleSerializer(page, many=True).data)


class OverdueRentsView(APIView):
    """GET /payments/rent/{rider_id}/overdue/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        overdue = RentSchedule.objects.filter(
            rider_id = rid,
            status   = "OVERDUE",
        ).order_by("due_date")

        from django.db.models import Sum
        total_overdue = overdue.aggregate(
            total=Sum("amount"),
            penalties=Sum("overdue_penalty"),
        )

        return ok({
            "count":           overdue.count(),
            "total_overdue":   float(total_overdue["total"] or 0),
            "total_penalties": float(total_overdue["penalties"] or 0),
            "schedules":       RentScheduleSerializer(overdue, many=True).data,
        })


class RentScheduleCreateView(APIView):
    """
    POST /payments/rent/schedule/create/
    Internal endpoint — called by fleet-service via Celery when vehicle is allocated.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def post(self, request):
        s = RentScheduleCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"success": False, "error": s.errors}, status=400)

        try:
            schedules = create_rent_schedule(
                allotment_id     = str(s.validated_data["allotment_id"]),
                rider_id         = str(s.validated_data["rider_id"]),
                daily_rent       = s.validated_data["daily_rent_amount"],
                start_date       = s.validated_data["start_date"],
                days             = s.validated_data["days"],
                security_deposit = s.validated_data["security_deposit"],
            )
            return ok({"schedules_created": len(schedules)}, 201)
        except Exception as e:
            logger.exception("Rent schedule creation failed")
            return err(str(e), 500)


# ─── Transactions ─────────────────────────────────────────────

class TransactionHistoryView(APIView):
    """GET /payments/transactions/{rider_id}/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        rid = _rider_id_from_request(request, rider_id)
        if not rid:
            return err("Access denied.", 403)

        qs = PaymentTransaction.objects.filter(rider_id=rid).order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(TransactionSerializer(page, many=True).data)


# ─── Razorpay Webhook ─────────────────────────────────────────

class RazorpayWebhookView(APIView):
    """
    POST /payments/webhooks/razorpay/
    Razorpay posts webhook events here.
    Must be public (no auth) but verified by HMAC signature.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.conf import settings
        from ..razorpay.client import verify_webhook_signature

        signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
        body      = request.body

        if not verify_webhook_signature(body, signature):
            logger.warning("Invalid Razorpay webhook signature")
            return err("Invalid signature", 400)

        try:
            payload    = json.loads(body)
            event_type = payload.get("event", "")
            handled    = handle_razorpay_webhook(event_type, payload)
            return ok({"received": True, "handled": handled})
        except Exception as e:
            logger.exception("Webhook processing failed")
            return err(str(e), 500)


# ─── Admin Summary ────────────────────────────────────────────

class AdminPaymentSummaryView(APIView):
    """
    GET /payments/admin/summary/
    Platform-wide payment metrics for the admin dashboard.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsFinanceOrAbove]

    def get(self, request):
        from django.db.models import Sum, Count, Q
        from django.utils import timezone
        from datetime import timedelta

        today          = timezone.now().date()
        yesterday      = today - timedelta(days=1)
        this_month_start = today.replace(day=1)

        ledger = WalletLedger.objects.aggregate(
            total_credits      = Sum("amount", filter=Q(direction="C")),
            total_debits       = Sum("amount", filter=Q(direction="D")),
            rent_collected_mtd = Sum("amount", filter=Q(
                direction="D",
                payment_type="DAILY_RENT",
                accounting_date__gte=this_month_start,
            )),
            rent_collected_today = Sum("amount", filter=Q(
                direction="D",
                payment_type="DAILY_RENT",
                accounting_date=today,
            )),
        )

        overdue = RentSchedule.objects.filter(status="OVERDUE").aggregate(
            count=Count("id"),
            total=Sum("amount"),
            penalties=Sum("overdue_penalty"),
        )

        wallets = RiderWallet.objects.aggregate(
            total_wallet_balance = Sum("balance"),
            total_deposits_held  = Sum("security_deposit_held"),
            active_wallets       = Count("id"),
        )

        return ok({
            "financial_summary": {
                "total_credits":       float(ledger["total_credits"] or 0),
                "total_debits":        float(ledger["total_debits"]  or 0),
                "rent_collected_today":float(ledger["rent_collected_today"] or 0),
                "rent_collected_mtd":  float(ledger["rent_collected_mtd"]  or 0),
            },
            "overdue": {
                "count":          overdue["count"] or 0,
                "total_amount":   float(overdue["total"]    or 0),
                "total_penalties": float(overdue["penalties"] or 0),
            },
            "wallets": {
                "total_balance":  float(wallets["total_wallet_balance"] or 0),
                "deposits_held":  float(wallets["total_deposits_held"]  or 0),
                "active_wallets": wallets["active_wallets"] or 0,
            },
        })
