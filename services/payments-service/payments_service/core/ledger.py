"""
payments_service/core/ledger.py

Double-entry ledger engine.
All money movements in the system go through here.

Rules:
  1. Every write is APPEND-ONLY on wallet_ledger
  2. wallet.balance is updated atomically using SELECT FOR UPDATE + version check
  3. No direct balance manipulation outside this module
  4. Every entry has a business reference (allotment_id, ticket_id, etc.)
"""
import logging
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone

from .models import RiderWallet, WalletLedger
from .exceptions import InsufficientBalanceError, WalletLockedError

logger = logging.getLogger(__name__)


def get_or_create_wallet(rider_id: str) -> RiderWallet:
    wallet, created = RiderWallet.objects.get_or_create(rider_id=rider_id)
    if created:
        logger.info("Created wallet for rider %s", rider_id)
    return wallet


@transaction.atomic
def credit(
    rider_id:       str,
    amount:         Decimal,
    payment_type:   str,
    description:    str     = "",
    reference_id:   Optional[str] = None,
    reference_type: Optional[str] = None,
    gateway:        Optional[str] = None,
    gateway_txn_id: Optional[str] = None,
    upi_ref_id:     Optional[str] = None,
) -> WalletLedger:
    """
    Credit rider wallet. Used for:
      - Incentive payments
      - Deposit refunds
      - Manual adjustments / top-ups
    """
    if amount <= 0:
        raise ValueError(f"Credit amount must be positive, got {amount}")

    wallet = RiderWallet.objects.select_for_update().get(rider_id=rider_id)

    old_balance   = wallet.balance
    new_balance   = old_balance + amount
    new_version   = wallet.version + 1

    wallet.balance      = new_balance
    wallet.total_earned = wallet.total_earned + amount
    wallet.version      = new_version
    wallet.save(update_fields=["balance", "total_earned", "version", "updated_at"])

    entry = WalletLedger.objects.create(
        wallet          = wallet,
        rider_id        = rider_id,
        payment_type    = payment_type,
        amount          = amount,
        direction       = "C",
        balance_after   = new_balance,
        reference_id    = reference_id,
        reference_type  = reference_type,
        description     = description,
        payment_gateway = gateway,
        gateway_txn_id  = gateway_txn_id,
        upi_ref_id      = upi_ref_id,
        accounting_date = timezone.now().date(),
    )

    logger.info(
        "CREDIT ₹%s to rider %s (%s) | balance: ₹%s → ₹%s",
        amount, rider_id, payment_type, old_balance, new_balance,
    )
    return entry


@transaction.atomic
def debit(
    rider_id:       str,
    amount:         Decimal,
    payment_type:   str,
    description:    str     = "",
    reference_id:   Optional[str] = None,
    reference_type: Optional[str] = None,
    gateway:        Optional[str] = None,
    gateway_txn_id: Optional[str] = None,
    allow_overdraft: bool   = False,
) -> WalletLedger:
    """
    Debit rider wallet. Used for:
      - Daily rent deduction
      - Security deposit hold
      - Penalties
    """
    from django.conf import settings

    if amount <= 0:
        raise ValueError(f"Debit amount must be positive, got {amount}")

    wallet = RiderWallet.objects.select_for_update().get(rider_id=rider_id)

    overdraft_limit = Decimal(settings.WALLET_OVERDRAFT_LIMIT)
    if not allow_overdraft and (wallet.balance - amount) < -overdraft_limit:
        raise InsufficientBalanceError(
            f"Insufficient balance. Available: ₹{wallet.balance}, "
            f"Required: ₹{amount}, Overdraft limit: ₹{overdraft_limit}"
        )

    old_balance = wallet.balance
    new_balance = old_balance - amount
    new_version = wallet.version + 1

    wallet.balance    = new_balance
    wallet.total_paid = wallet.total_paid + amount
    wallet.version    = new_version
    wallet.save(update_fields=["balance", "total_paid", "version", "updated_at"])

    entry = WalletLedger.objects.create(
        wallet          = wallet,
        rider_id        = rider_id,
        payment_type    = payment_type,
        amount          = amount,
        direction       = "D",
        balance_after   = new_balance,
        reference_id    = reference_id,
        reference_type  = reference_type,
        description     = description,
        payment_gateway = gateway,
        gateway_txn_id  = gateway_txn_id,
        accounting_date = timezone.now().date(),
    )

    logger.info(
        "DEBIT ₹%s from rider %s (%s) | balance: ₹%s → ₹%s",
        amount, rider_id, payment_type, old_balance, new_balance,
    )
    return entry


@transaction.atomic
def hold_security_deposit(rider_id: str, amount: Decimal, allotment_id: str) -> WalletLedger:
    """
    Hold security deposit. Debits wallet and updates security_deposit_held counter.
    """
    entry = debit(
        rider_id       = rider_id,
        amount         = amount,
        payment_type   = "SECURITY_DEPOSIT",
        description    = f"Security deposit for allotment {allotment_id}",
        reference_id   = allotment_id,
        reference_type = "ALLOTMENT",
        allow_overdraft = False,
    )
    # Update held counter
    RiderWallet.objects.filter(rider_id=rider_id).update(
        security_deposit_held=entry.wallet.security_deposit_held + amount
    )
    return entry


@transaction.atomic
def release_security_deposit(rider_id: str, amount: Decimal, allotment_id: str) -> WalletLedger:
    """
    Release (refund) security deposit back to wallet.
    """
    entry = credit(
        rider_id       = rider_id,
        amount         = amount,
        payment_type   = "DEPOSIT_REFUND",
        description    = f"Security deposit refund for allotment {allotment_id}",
        reference_id   = allotment_id,
        reference_type = "ALLOTMENT",
    )
    # Reduce held counter
    wallet = RiderWallet.objects.get(rider_id=rider_id)
    new_held = max(Decimal("0"), wallet.security_deposit_held - amount)
    wallet.security_deposit_held = new_held
    wallet.save(update_fields=["security_deposit_held", "updated_at"])
    return entry


def get_wallet_summary(rider_id: str) -> dict:
    """
    Returns current wallet state plus a 30-day ledger summary.
    """
    from django.db.models import Sum, Q
    from datetime import timedelta

    wallet = get_or_create_wallet(rider_id)

    thirty_days_ago = timezone.now().date() - timedelta(days=30)

    summary = WalletLedger.objects.filter(
        rider_id=rider_id,
        accounting_date__gte=thirty_days_ago,
    ).aggregate(
        credits_30d = Sum("amount", filter=Q(direction="C")),
        debits_30d  = Sum("amount", filter=Q(direction="D")),
    )

    # Pending dues from rent schedule
    from .models import RentSchedule
    pending = RentSchedule.objects.filter(
        rider_id=rider_id,
        status__in=["PENDING", "OVERDUE"],
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "wallet_id":            str(wallet.id),
        "balance":              float(wallet.balance),
        "total_earned":         float(wallet.total_earned),
        "total_paid":           float(wallet.total_paid),
        "security_deposit_held": float(wallet.security_deposit_held),
        "pending_dues":         float(pending),
        "credits_last_30d":     float(summary["credits_30d"] or 0),
        "debits_last_30d":      float(summary["debits_30d"]  or 0),
        "net_last_30d":         float((summary["credits_30d"] or 0) - (summary["debits_30d"] or 0)),
    }
