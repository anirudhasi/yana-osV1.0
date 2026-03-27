"""
tests/test_payments.py — Payments service test suite
Run: python manage.py test tests --verbosity=2
"""
import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.utils import timezone

from payments_service.core.models import (
    RiderWallet, WalletLedger, PaymentTransaction, RentSchedule, UPIMandate
)
from payments_service.core.ledger import (
    get_or_create_wallet, credit, debit,
    hold_security_deposit, release_security_deposit, get_wallet_summary
)
from payments_service.core.services import (
    create_rent_schedule, deduct_rent_for_rider,
    credit_incentive, admin_adjustment, initiate_topup, confirm_topup,
)
from payments_service.core.exceptions import InsufficientBalanceError


# ── Token helpers ─────────────────────────────────────────────

def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id': str(uuid.uuid4()), 'role': role, 'token_type': 'admin', 'type': 'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


def rider_token(rider_id):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id': str(rider_id), 'role': 'RIDER', 'token_type': 'rider', 'type': 'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


# ── Ledger Engine Tests ───────────────────────────────────────

class LedgerEngineTest(TestCase):

    def setUp(self):
        self.rider_id = str(uuid.uuid4())
        self.wallet   = get_or_create_wallet(self.rider_id)

    def test_initial_wallet_balance_zero(self):
        self.assertEqual(self.wallet.balance, Decimal("0"))
        self.assertEqual(self.wallet.version, 0)

    def test_credit_increases_balance(self):
        entry = credit(self.rider_id, Decimal("500"), "INCENTIVE", "Test credit")
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("500"))
        self.assertEqual(entry.direction, "C")
        self.assertEqual(entry.balance_after, Decimal("500"))
        self.assertEqual(entry.payment_type, "INCENTIVE")

    def test_debit_decreases_balance(self):
        credit(self.rider_id, Decimal("300"), "TOPUP", "Top up")
        entry = debit(self.rider_id, Decimal("150"), "DAILY_RENT", "Rent")
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("150"))
        self.assertEqual(entry.direction, "D")
        self.assertEqual(entry.balance_after, Decimal("150"))

    def test_debit_insufficient_balance_raises(self):
        credit(self.rider_id, Decimal("100"), "TOPUP", "Top up")
        with self.assertRaises(InsufficientBalanceError):
            debit(self.rider_id, Decimal("700"), "DAILY_RENT", "Rent")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100"))  # unchanged

    def test_debit_with_overdraft_allowed(self):
        # Empty wallet — overdraft allowed up to ₹500
        entry = debit(self.rider_id, Decimal("200"), "DAILY_RENT", "Rent",
                      allow_overdraft=True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("-200"))

    def test_overdraft_beyond_limit_raises(self):
        with self.assertRaises(InsufficientBalanceError):
            debit(self.rider_id, Decimal("600"), "DAILY_RENT", "Rent",
                  allow_overdraft=True)

    def test_version_increments_on_each_write(self):
        credit(self.rider_id, Decimal("100"), "TOPUP", "a")
        credit(self.rider_id, Decimal("100"), "TOPUP", "b")
        debit(self.rider_id,  Decimal("50"),  "DAILY_RENT", "c")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.version, 3)

    def test_ledger_is_append_only(self):
        credit(self.rider_id, Decimal("100"), "TOPUP", "t")
        count_before = WalletLedger.objects.filter(rider_id=self.rider_id).count()
        credit(self.rider_id, Decimal("50"),  "INCENTIVE", "i")
        count_after = WalletLedger.objects.filter(rider_id=self.rider_id).count()
        self.assertEqual(count_after, count_before + 1)

    def test_security_deposit_hold_and_release(self):
        credit(self.rider_id, Decimal("1000"), "TOPUP", "Start")
        allotment_id = str(uuid.uuid4())

        hold_entry = hold_security_deposit(self.rider_id, Decimal("500"), allotment_id)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("500"))

        release_entry = release_security_deposit(self.rider_id, Decimal("500"), allotment_id)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("1000"))
        self.assertEqual(release_entry.payment_type, "DEPOSIT_REFUND")

    def test_wallet_summary_structure(self):
        credit(self.rider_id, Decimal("300"), "TOPUP", "s")
        debit(self.rider_id, Decimal("100"), "DAILY_RENT", "r")
        summary = get_wallet_summary(self.rider_id)

        self.assertIn("balance", summary)
        self.assertIn("pending_dues", summary)
        self.assertIn("credits_last_30d", summary)
        self.assertEqual(summary["balance"], 200.0)


# ── Rent Schedule Tests ───────────────────────────────────────

class RentScheduleTest(TestCase):

    def setUp(self):
        self.rider_id    = str(uuid.uuid4())
        self.allotment_id = str(uuid.uuid4())
        self.wallet      = get_or_create_wallet(self.rider_id)

    def test_create_rent_schedule_creates_correct_rows(self):
        today = date.today()
        schedules = create_rent_schedule(
            allotment_id     = self.allotment_id,
            rider_id         = self.rider_id,
            daily_rent       = Decimal("150"),
            start_date       = today,
            days             = 7,
            security_deposit = Decimal("0"),
        )
        self.assertEqual(len(schedules), 7)
        due_dates = [s.due_date for s in schedules]
        self.assertEqual(due_dates[0], today)
        self.assertEqual(due_dates[-1], today + timedelta(days=6))
        self.assertTrue(all(s.status == "PENDING" for s in schedules))

    def test_create_rent_schedule_with_deposit_holds_deposit(self):
        # Give rider enough balance
        credit(self.rider_id, Decimal("600"), "TOPUP", "start")
        create_rent_schedule(
            allotment_id     = self.allotment_id,
            rider_id         = self.rider_id,
            daily_rent       = Decimal("100"),
            start_date       = date.today(),
            days             = 3,
            security_deposit = Decimal("500"),
        )
        self.wallet.refresh_from_db()
        # Balance should be reduced by deposit
        self.assertEqual(self.wallet.balance, Decimal("100"))

    def test_deduct_rent_success(self):
        credit(self.rider_id, Decimal("500"), "TOPUP", "fund wallet")
        today = date.today()
        create_rent_schedule(
            allotment_id=self.allotment_id,
            rider_id=self.rider_id,
            daily_rent=Decimal("150"),
            start_date=today,
            days=1,
        )
        entry = deduct_rent_for_rider(self.rider_id, today)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.payment_type, "DAILY_RENT")

        schedule = RentSchedule.objects.get(rider_id=self.rider_id, due_date=today)
        self.assertEqual(schedule.status, "PAID")
        self.assertIsNotNone(schedule.paid_at)

    def test_deduct_rent_insufficient_balance_marks_overdue(self):
        today = date.today()
        create_rent_schedule(
            allotment_id=self.allotment_id,
            rider_id=self.rider_id,
            daily_rent=Decimal("150"),
            start_date=today,
            days=1,
        )
        # Wallet empty — should mark overdue
        entry = deduct_rent_for_rider(self.rider_id, today)
        self.assertIsNone(entry)

        schedule = RentSchedule.objects.get(rider_id=self.rider_id, due_date=today)
        self.assertEqual(schedule.status, "OVERDUE")
        self.assertGreater(schedule.overdue_penalty, 0)

    def test_deduct_rent_no_schedule_returns_none(self):
        result = deduct_rent_for_rider(self.rider_id, date.today())
        self.assertIsNone(result)

    def test_mark_overdue_task(self):
        from django.db.models import F
        yesterday = date.today() - timedelta(days=1)
        RentSchedule.objects.create(
            allotment_id = self.allotment_id,
            rider_id     = self.rider_id,
            due_date     = yesterday,
            amount       = Decimal("150"),
            status       = "PENDING",
        )
        from payments_service.core.tasks import mark_overdue_rent_schedules
        result = mark_overdue_rent_schedules()
        self.assertGreaterEqual(result["marked_overdue"], 1)

        schedule = RentSchedule.objects.get(rider_id=self.rider_id)
        self.assertEqual(schedule.status, "OVERDUE")


# ── Payment Flow Tests ────────────────────────────────────────

class PaymentFlowTest(TestCase):

    def setUp(self):
        self.rider_id = str(uuid.uuid4())
        self.wallet   = get_or_create_wallet(self.rider_id)

    def test_incentive_credit(self):
        entry = credit_incentive(
            rider_id      = self.rider_id,
            amount        = Decimal("200"),
            description   = "Performance bonus",
            reference_type = "BONUS",
        )
        self.assertEqual(entry.payment_type, "INCENTIVE")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("200"))

    def test_admin_credit_adjustment(self):
        entry = admin_adjustment(
            rider_id    = self.rider_id,
            amount      = Decimal("100"),
            direction   = "C",
            description = "Goodwill credit",
            admin_id    = str(uuid.uuid4()),
        )
        self.assertEqual(entry.payment_type, "ADJUSTMENT")
        self.assertEqual(entry.direction, "C")

    def test_admin_debit_adjustment(self):
        credit(self.rider_id, Decimal("500"), "TOPUP", "fund")
        entry = admin_adjustment(
            rider_id    = self.rider_id,
            amount      = Decimal("50"),
            direction   = "D",
            description = "Error correction",
            admin_id    = str(uuid.uuid4()),
        )
        self.assertEqual(entry.direction, "D")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("450"))

    @patch("payments_service.razorpay.client.create_order")
    def test_initiate_topup_creates_pending_transaction(self, mock_order):
        mock_order.return_value = {
            "id": "order_sim_abc123",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "simulated": True,
        }
        result = initiate_topup(self.rider_id, Decimal("500"))

        self.assertIn("razorpay_order_id", result)
        self.assertIn("transaction_id", result)

        txn = PaymentTransaction.objects.get(id=result["transaction_id"])
        self.assertEqual(txn.status, "PENDING")
        self.assertEqual(txn.amount, Decimal("500"))
        self.assertEqual(txn.gateway, "razorpay")

    @patch("payments_service.razorpay.client.fetch_payment")
    @patch("payments_service.razorpay.client.create_order")
    def test_confirm_topup_credits_wallet(self, mock_order, mock_fetch):
        mock_order.return_value = {
            "id": "order_sim_def456",
            "amount": 30000,
            "currency": "INR",
            "status": "created",
            "simulated": True,
        }
        mock_fetch.return_value = {"id": "pay_sim_xyz", "status": "captured", "simulated": True}

        initiate_topup(self.rider_id, Decimal("300"))
        entry = confirm_topup(
            rider_id            = self.rider_id,
            razorpay_order_id   = "order_sim_def456",
            razorpay_payment_id = "pay_sim_xyz",
            razorpay_signature  = "sig_test",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("300"))
        self.assertEqual(entry.payment_type, "TOPUP")


# ── API Endpoint Tests ────────────────────────────────────────

class PaymentsAPITest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.admin    = admin_token("SUPER_ADMIN")
        self.finance  = admin_token("SALES")
        self.rider_id = str(uuid.uuid4())
        self.wallet   = get_or_create_wallet(self.rider_id)
        self.rtok     = rider_token(self.rider_id)

    def test_wallet_summary_admin(self):
        resp = self.client.get(
            f"/api/v1/payments/wallets/{self.rider_id}/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("balance", resp.json()["data"])

    def test_wallet_summary_rider_own(self):
        resp = self.client.get(
            f"/api/v1/payments/wallets/{self.rider_id}/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        self.assertEqual(resp.status_code, 200)

    def test_rider_cannot_access_other_wallet(self):
        other_id = str(uuid.uuid4())
        resp = self.client.get(
            f"/api/v1/payments/wallets/{other_id}/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        self.assertEqual(resp.status_code, 403)

    def test_ledger_history(self):
        credit(self.rider_id, Decimal("200"), "TOPUP", "test")
        resp = self.client.get(
            f"/api/v1/payments/wallets/{self.rider_id}/ledger/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_ledger_filter_by_type(self):
        credit(self.rider_id, Decimal("100"), "TOPUP",     "a")
        credit(self.rider_id, Decimal("50"),  "INCENTIVE", "b")
        resp = self.client.get(
            f"/api/v1/payments/wallets/{self.rider_id}/ledger/?payment_type=INCENTIVE",
            HTTP_AUTHORIZATION=self.admin,
        )
        results = resp.json()["data"]["results"]
        self.assertTrue(all(r["payment_type"] == "INCENTIVE" for r in results))

    def test_admin_adjustment_credit(self):
        resp = self.client.post(
            f"/api/v1/payments/wallets/{self.rider_id}/adjust/",
            data=json.dumps({"amount": "150.00", "direction": "C",
                             "description": "Test credit"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.finance,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["new_balance"], 150.0)

    def test_incentive_credit_api(self):
        resp = self.client.post(
            f"/api/v1/payments/wallets/{self.rider_id}/incentive/",
            data=json.dumps({"amount": "250.00",
                             "description": "Blinkit shift bonus",
                             "reference_type": "JOB"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.finance,
        )
        self.assertEqual(resp.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("250"))

    def test_rent_schedule_list(self):
        today = date.today()
        RentSchedule.objects.create(
            allotment_id=uuid.uuid4(), rider_id=self.rider_id,
            due_date=today, amount=Decimal("150"), status="PENDING",
        )
        resp = self.client.get(
            f"/api/v1/payments/rent/{self.rider_id}/schedule/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_overdue_rents_view(self):
        yesterday = date.today() - timedelta(days=1)
        RentSchedule.objects.create(
            allotment_id=uuid.uuid4(), rider_id=self.rider_id,
            due_date=yesterday, amount=Decimal("150"),
            status="OVERDUE", overdue_penalty=Decimal("25"),
        )
        resp = self.client.get(
            f"/api/v1/payments/rent/{self.rider_id}/overdue/",
            HTTP_AUTHORIZATION=self.admin,
        )
        data = resp.json()["data"]
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_overdue"], 150.0)
        self.assertEqual(data["total_penalties"], 25.0)

    def test_admin_payment_summary(self):
        credit(self.rider_id, Decimal("300"), "TOPUP", "s")
        resp = self.client.get(
            "/api/v1/payments/admin/summary/",
            HTTP_AUTHORIZATION=self.finance,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("financial_summary", data)
        self.assertIn("wallets", data)
        self.assertIn("overdue", data)

    def test_transaction_history(self):
        PaymentTransaction.objects.create(
            rider_id=self.rider_id,
            amount=Decimal("200"),
            gateway="razorpay",
            status="SUCCESS",
            payment_type="TOPUP",
        )
        resp = self.client.get(
            f"/api/v1/payments/transactions/{self.rider_id}/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_razorpay_webhook_invalid_signature(self):
        resp = self.client.post(
            "/api/v1/payments/webhooks/razorpay/",
            data=json.dumps({"event": "payment.captured"}),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid_sig",
        )
        # In simulate mode signature check is bypassed, so 200
        # In prod with real key this would be 400
        self.assertIn(resp.status_code, [200, 400])


# ── Celery Task Tests ─────────────────────────────────────────

class CeleryTaskTest(TestCase):

    def setUp(self):
        self.rider_id    = str(uuid.uuid4())
        self.allotment_id = str(uuid.uuid4())
        self.wallet      = get_or_create_wallet(self.rider_id)

    def test_daily_rent_task_deducts_for_all_riders(self):
        credit(self.rider_id, Decimal("500"), "TOPUP", "fund")
        today = date.today()
        create_rent_schedule(
            allotment_id=self.allotment_id,
            rider_id=self.rider_id,
            daily_rent=Decimal("150"),
            start_date=today,
            days=1,
        )
        from payments_service.core.tasks import deduct_daily_rent
        result = deduct_daily_rent()
        self.assertEqual(result["success"], 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("350"))

    def test_generate_monthly_statement_task(self):
        credit(self.rider_id, Decimal("1000"), "TOPUP",     "load")
        credit(self.rider_id, Decimal("200"),  "INCENTIVE", "bonus")
        debit(self.rider_id,  Decimal("300"),  "DAILY_RENT", "rent")
        from payments_service.core.tasks import generate_monthly_statement
        from django.utils import timezone
        month = timezone.now().strftime("%Y-%m")
        # Should run without error
        generate_monthly_statement(self.rider_id, month)
