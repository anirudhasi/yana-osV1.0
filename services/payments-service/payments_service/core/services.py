"""
payments_service/core/services.py

Business logic:
  - Rent schedule creation
  - Daily rent deduction
  - Top-up / withdrawal
  - Razorpay payment flow
  - UPI mandate management
  - Incentive crediting
"""
import logging
import uuid
from decimal import Decimal
from typing import Optional, List
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    RiderWallet, WalletLedger, PaymentTransaction, RentSchedule, UPIMandate
)
from .ledger import (
    get_or_create_wallet, credit, debit,
    hold_security_deposit, release_security_deposit
)
from .exceptions import (
    InsufficientBalanceError, GatewayError,
    RentScheduleError, DuplicateTransactionError
)
from ..razorpay import client as razorpay_client

logger = logging.getLogger(__name__)


# ─── Wallet creation ──────────────────────────────────────────

def ensure_wallet(rider_id: str) -> RiderWallet:
    return get_or_create_wallet(rider_id)


# ─── Rent schedule ────────────────────────────────────────────

@transaction.atomic
def create_rent_schedule(
    allotment_id:     str,
    rider_id:         str,
    daily_rent:       Decimal,
    start_date:       date,
    days:             int = 30,
    security_deposit: Decimal = Decimal("0"),
) -> List[RentSchedule]:
    """
    Create daily rent schedule rows for a new allotment.
    Called by Celery task when fleet-service publishes vehicle.allocated event.
    Creates `days` future rent entries.
    Also holds the security deposit.
    """
    wallet = ensure_wallet(rider_id)

    # Hold security deposit if present
    if security_deposit > 0:
        try:
            hold_security_deposit(rider_id, security_deposit, allotment_id)
            # Update wallet pending dues
            wallet.total_pending_dues += security_deposit
            wallet.save(update_fields=["total_pending_dues", "updated_at"])
        except InsufficientBalanceError as e:
            logger.warning("Cannot hold deposit for rider %s: %s", rider_id, e)

    # Generate rent rows
    schedules = []
    for i in range(days):
        due = start_date + timedelta(days=i)
        schedules.append(RentSchedule(
            allotment_id = allotment_id,
            rider_id     = rider_id,
            due_date     = due,
            amount       = daily_rent,
            status       = "PENDING",
        ))

    created = RentSchedule.objects.bulk_create(schedules)

    # Update wallet pending dues
    total_pending = daily_rent * days
    RiderWallet.objects.filter(rider_id=rider_id).update(
        total_pending_dues=wallet.total_pending_dues + total_pending
    )

    logger.info(
        "Created %d rent schedule entries for allotment %s (rider %s, ₹%s/day)",
        len(created), allotment_id, rider_id, daily_rent,
    )
    return created


@transaction.atomic
def deduct_rent_for_rider(rider_id: str, due_date: date) -> Optional[WalletLedger]:
    """
    Deduct today's rent for a single rider.
    Called by Celery beat task daily.
    Returns ledger entry or None if no rent due today.
    """
    schedule = RentSchedule.objects.filter(
        rider_id  = rider_id,
        due_date  = due_date,
        status__in = ["PENDING", "OVERDUE"],
    ).select_for_update().first()

    if not schedule:
        return None

    total_due = schedule.amount + schedule.overdue_penalty

    try:
        entry = debit(
            rider_id       = rider_id,
            amount         = total_due,
            payment_type   = "DAILY_RENT",
            description    = f"Daily rent for {due_date} (allotment {schedule.allotment_id})",
            reference_id   = str(schedule.allotment_id),
            reference_type = "ALLOTMENT",
            allow_overdraft = True,  # Allow small overdraft for rent
        )
        schedule.status       = "PAID"
        schedule.paid_ledger  = entry
        schedule.paid_at      = timezone.now()
        schedule.save(update_fields=["status", "paid_ledger", "paid_at", "updated_at"])

        # Reduce pending dues counter
        RiderWallet.objects.filter(rider_id=rider_id).update(
            total_pending_dues=max(Decimal("0"), RiderWallet.objects.get(rider_id=rider_id).total_pending_dues - total_due)
        )

        logger.info("Rent deducted ₹%s for rider %s on %s", total_due, rider_id, due_date)
        return entry

    except InsufficientBalanceError as e:
        # Mark as overdue, apply penalty
        _apply_overdue_penalty(schedule)
        logger.warning("Insufficient balance for rider %s rent on %s: %s", rider_id, due_date, e)
        return None


def _apply_overdue_penalty(schedule: RentSchedule):
    from django.conf import settings
    penalty_per_day = Decimal(settings.OVERDUE_PENALTY_PER_DAY)

    schedule.status          = "OVERDUE"
    schedule.days_overdue    = schedule.days_overdue + 1
    schedule.overdue_penalty = schedule.overdue_penalty + penalty_per_day
    schedule.penalty_applied_at = timezone.now()
    schedule.save(update_fields=[
        "status", "days_overdue", "overdue_penalty", "penalty_applied_at", "updated_at"
    ])
    logger.warning("Applied ₹%s overdue penalty for rider %s (schedule %s)",
                   penalty_per_day, schedule.rider_id, schedule.id)


# ─── Top-up (Razorpay payment) ────────────────────────────────

@transaction.atomic
def initiate_topup(rider_id: str, amount: Decimal) -> dict:
    """
    Initiate a wallet top-up via Razorpay.
    Returns Razorpay order details for the client to complete payment.
    """
    if amount < Decimal("10"):
        raise GatewayError("Minimum top-up amount is ₹10.")
    if amount > Decimal("10000"):
        raise GatewayError("Maximum single top-up is ₹10,000.")

    wallet  = ensure_wallet(rider_id)
    receipt = f"topup_{rider_id[:8]}_{uuid.uuid4().hex[:8]}"

    # Create Razorpay order
    order = razorpay_client.create_order(amount, receipt, notes={"rider_id": str(rider_id)})

    # Create a PENDING transaction record
    txn = PaymentTransaction.objects.create(
        rider_id         = rider_id,
        amount           = amount,
        gateway          = "razorpay",
        gateway_order_id = order["id"],
        status           = "PENDING",
        payment_type     = "TOPUP",
    )

    return {
        "transaction_id":  str(txn.id),
        "razorpay_order_id": order["id"],
        "amount":          float(amount),
        "currency":        "INR",
        "key_id":          "settings.RAZORPAY_KEY_ID",  # send to client
        "receipt":         receipt,
        "simulated":       order.get("simulated", False),
    }


@transaction.atomic
def confirm_topup(
    rider_id:          str,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> WalletLedger:
    """
    Called after rider completes Razorpay payment on mobile.
    Verifies payment and credits wallet.
    """
    try:
        txn = PaymentTransaction.objects.select_for_update().get(
            gateway_order_id = razorpay_order_id,
            rider_id         = rider_id,
            status           = "PENDING",
        )
    except PaymentTransaction.DoesNotExist:
        raise GatewayError("Transaction not found or already processed.")

    # Verify with Razorpay
    payment = razorpay_client.fetch_payment(razorpay_payment_id)
    if not payment.get("simulated") and payment.get("status") != "captured":
        # Capture if not auto-captured
        razorpay_client.capture_payment(razorpay_payment_id, txn.amount)

    # Update transaction
    txn.gateway_payment_id  = razorpay_payment_id
    txn.gateway_signature   = razorpay_signature
    txn.gateway_status      = "captured"
    txn.gateway_raw_response = payment
    txn.status              = "SUCCESS"
    txn.completed_at        = timezone.now()
    txn.save()

    # Credit wallet via ledger
    entry = credit(
        rider_id       = rider_id,
        amount         = txn.amount,
        payment_type   = "TOPUP",
        description    = f"Wallet top-up via Razorpay",
        gateway        = "razorpay",
        gateway_txn_id = razorpay_payment_id,
    )

    # Link ledger entry to transaction
    txn.ledger_entry = entry
    txn.save(update_fields=["ledger_entry"])

    logger.info("Top-up confirmed: ₹%s for rider %s", txn.amount, rider_id)
    return entry


# ─── Webhook handler ──────────────────────────────────────────

@transaction.atomic
def handle_razorpay_webhook(event_type: str, payload: dict) -> bool:
    """
    Process Razorpay webhook events.
    Returns True if handled, False if ignored.
    """
    logger.info("Razorpay webhook: %s", event_type)

    if event_type == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id    = payment.get("order_id")
        payment_id  = payment.get("id")
        amount_paise = payment.get("amount", 0)

        try:
            txn = PaymentTransaction.objects.get(
                gateway_order_id=order_id, status="PENDING"
            )
        except PaymentTransaction.DoesNotExist:
            logger.warning("Webhook: unknown order_id %s", order_id)
            return False

        if txn.status == "SUCCESS":
            return True  # Already processed (idempotent)

        txn.gateway_payment_id  = payment_id
        txn.gateway_status      = "captured"
        txn.gateway_raw_response = payment
        txn.status              = "SUCCESS"
        txn.completed_at        = timezone.now()
        txn.save()

        entry = credit(
            rider_id       = str(txn.rider_id),
            amount         = Decimal(amount_paise) / 100,
            payment_type   = txn.payment_type or "TOPUP",
            description    = f"Razorpay webhook: {event_type}",
            gateway        = "razorpay",
            gateway_txn_id = payment_id,
        )
        txn.ledger_entry = entry
        txn.save(update_fields=["ledger_entry"])
        return True

    if event_type == "payment.failed":
        payment  = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment.get("order_id")
        try:
            txn = PaymentTransaction.objects.get(gateway_order_id=order_id, status="PENDING")
            txn.status         = "FAILED"
            txn.failure_reason = payment.get("error_description", "Payment failed")
            txn.gateway_raw_response = payment
            txn.save(update_fields=["status", "failure_reason", "gateway_raw_response", "updated_at"])
        except PaymentTransaction.DoesNotExist:
            pass
        return True

    # Unhandled event — still return 200 to Razorpay
    return False


# ─── Incentive crediting ──────────────────────────────────────

@transaction.atomic
def credit_incentive(
    rider_id:      str,
    amount:        Decimal,
    description:   str,
    reference_id:  Optional[str] = None,
    reference_type: str = "JOB",
) -> WalletLedger:
    """Credit an incentive or bonus to a rider wallet."""
    if amount <= 0:
        raise GatewayError("Incentive amount must be positive.")

    entry = credit(
        rider_id       = rider_id,
        amount         = amount,
        payment_type   = "INCENTIVE",
        description    = description,
        reference_id   = reference_id,
        reference_type = reference_type,
    )
    logger.info("Incentive ₹%s credited to rider %s", amount, rider_id)
    return entry


# ─── Manual adjustment ────────────────────────────────────────

@transaction.atomic
def admin_adjustment(
    rider_id:    str,
    amount:      Decimal,
    direction:   str,
    description: str,
    admin_id:    str,
) -> WalletLedger:
    """
    Admin manually credits or debits a wallet.
    direction: 'C' (credit) or 'D' (debit)
    """
    if direction == "C":
        return credit(
            rider_id=rider_id, amount=amount,
            payment_type="ADJUSTMENT", description=f"Admin adjustment: {description}",
            gateway="manual",
        )
    else:
        return debit(
            rider_id=rider_id, amount=amount,
            payment_type="ADJUSTMENT", description=f"Admin adjustment: {description}",
            gateway="manual", allow_overdraft=True,
        )


# ─── UPI AutoPay mandate ──────────────────────────────────────

@transaction.atomic
def setup_upi_autopay(
    rider_id:    str,
    upi_id:      str,
    rider_name:  str,
    rider_phone: str,
    max_amount:  Decimal = Decimal("500"),
) -> UPIMandate:
    """Create or update UPI AutoPay mandate for a rider."""
    result = razorpay_client.create_upi_autopay_mandate(
        rider_id, upi_id, max_amount, rider_name, rider_phone
    )
    mandate, _ = UPIMandate.objects.update_or_create(
        rider_id=rider_id,
        defaults={
            "upi_id":               upi_id,
            "razorpay_mandate_id":  result["mandate_id"],
            "razorpay_customer_id": result.get("customer_id"),
            "max_amount":           max_amount,
            "is_active":            True,
            "activated_at":         timezone.now(),
        },
    )
    logger.info("UPI AutoPay mandate set up for rider %s (mandate: %s)",
                rider_id, result["mandate_id"])
    return mandate


@transaction.atomic
def revoke_upi_autopay(rider_id: str) -> UPIMandate:
    mandate = UPIMandate.objects.get(rider_id=rider_id)
    mandate.is_active  = False
    mandate.revoked_at = timezone.now()
    mandate.save(update_fields=["is_active", "revoked_at", "updated_at"])
    return mandate
