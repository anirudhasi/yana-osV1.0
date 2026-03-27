#!/bin/bash
# =============================================================
# Yana OS — Payments Service API Testing
# Payments Service: http://localhost:8004
# Via gateway:      http://localhost:8000/api/v1/payments/
# =============================================================

ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yana.in","password":"Admin@123"}' \
  | jq -r '.data.tokens.access_token')

echo "Admin token: ${ADMIN_TOKEN:0:30}..."

# Replace with a real rider UUID from your seed data
RIDER_ID="<paste-rider-uuid-here>"

# ─────────────────────────────────────────────────────────────
# WALLET SUMMARY
# ─────────────────────────────────────────────────────────────

curl -s http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# ─────────────────────────────────────────────────────────────
# LEDGER HISTORY
# ─────────────────────────────────────────────────────────────

# Full ledger
curl -s "http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/ledger/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {count, results: [.results[].payment_type]}'

# Filter by type
curl -s "http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/ledger/?payment_type=DAILY_RENT" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Filter by direction (Credits only)
curl -s "http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/ledger/?direction=C" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].amount'

# Filter by date range
curl -s "http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/ledger/?from_date=2025-01-01&to_date=2025-12-31" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# ─────────────────────────────────────────────────────────────
# TOP-UP FLOW (Razorpay)
# ─────────────────────────────────────────────────────────────

# Step 1: Initiate top-up
TOPUP=$(curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/topup/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"amount": "500.00"}')

echo "Top-up initiated:"
echo $TOPUP | jq '{transaction_id: .data.transaction_id, order_id: .data.razorpay_order_id}'

ORDER_ID=$(echo $TOPUP | jq -r '.data.razorpay_order_id')
TXN_ID=$(echo $TOPUP | jq -r '.data.transaction_id')

# Step 2: Confirm (after rider completes payment on mobile)
# In simulation mode, use any payment_id
curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/topup/confirm/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"razorpay_order_id\":   \"$ORDER_ID\",
    \"razorpay_payment_id\": \"pay_sim_test123\",
    \"razorpay_signature\":  \"sig_test\"
  }" | jq '.data | {new_balance, ledger_entry: .ledger_entry.payment_type}'

# ─────────────────────────────────────────────────────────────
# ADMIN ADJUSTMENTS
# ─────────────────────────────────────────────────────────────

# Credit adjustment
curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/adjust/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"amount":"100.00","direction":"C","description":"Goodwill credit for app issue"}' \
  | jq '.data.new_balance'

# Debit adjustment
curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/adjust/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"amount":"25.00","direction":"D","description":"Error correction"}' \
  | jq '.data.new_balance'

# ─────────────────────────────────────────────────────────────
# INCENTIVE CREDITING
# ─────────────────────────────────────────────────────────────

curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/incentive/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "amount":         "250.00",
    "description":    "Blinkit shift completion bonus — 30 orders",
    "reference_type": "JOB"
  }' | jq '.data | {new_balance}'

# ─────────────────────────────────────────────────────────────
# UPI AUTOPAY MANDATE
# ─────────────────────────────────────────────────────────────

# Setup mandate
curl -s -X POST http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/upi-mandate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "upi_id":      "rider@sbi",
    "rider_name":  "Rajesh Kumar",
    "rider_phone": "9876543210",
    "max_amount":  "200.00"
  }' | jq '.data | {upi_id, is_active}'

# Get mandate
curl -s http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/upi-mandate/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {upi_id, is_active}'

# Revoke mandate
curl -s -X DELETE http://localhost:8000/api/v1/payments/wallets/$RIDER_ID/upi-mandate/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.message'

# ─────────────────────────────────────────────────────────────
# RENT SCHEDULE
# ─────────────────────────────────────────────────────────────

# Create schedule (normally called by Celery on vehicle allocation)
ALLOTMENT_ID="<paste-allotment-uuid-here>"
curl -s -X POST http://localhost:8000/api/v1/payments/rent/schedule/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"allotment_id\":      \"$ALLOTMENT_ID\",
    \"rider_id\":          \"$RIDER_ID\",
    \"daily_rent_amount\": \"150.00\",
    \"security_deposit\":  \"500.00\",
    \"start_date\":        \"$(date +%Y-%m-%d)\",
    \"days\":              30
  }" | jq '.data.schedules_created'

# View rent schedule
curl -s "http://localhost:8000/api/v1/payments/rent/$RIDER_ID/schedule/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.data | {count, sample: .results[:3] | [.[].due_date]}'

# Filter pending only
curl -s "http://localhost:8000/api/v1/payments/rent/$RIDER_ID/schedule/?status=PENDING" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Overdue rents
curl -s "http://localhost:8000/api/v1/payments/rent/$RIDER_ID/overdue/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.data | {count, total_overdue, total_penalties}'

# ─────────────────────────────────────────────────────────────
# TRANSACTION HISTORY
# ─────────────────────────────────────────────────────────────

curl -s "http://localhost:8000/api/v1/payments/transactions/$RIDER_ID/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.data | {count, statuses: [.results[].status]}'

# Filter by status
curl -s "http://localhost:8000/api/v1/payments/transactions/$RIDER_ID/?status=SUCCESS" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# ─────────────────────────────────────────────────────────────
# RAZORPAY WEBHOOK SIMULATION
# ─────────────────────────────────────────────────────────────

curl -s -X POST http://localhost:8000/api/v1/payments/webhooks/razorpay/ \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: sim_signature" \
  -d "{
    \"event\": \"payment.captured\",
    \"payload\": {
      \"payment\": {
        \"entity\": {
          \"id\":       \"pay_webhook_test\",
          \"order_id\": \"$ORDER_ID\",
          \"amount\":   50000,
          \"status\":   \"captured\"
        }
      }
    }
  }" | jq .

# ─────────────────────────────────────────────────────────────
# ADMIN PLATFORM SUMMARY
# ─────────────────────────────────────────────────────────────

curl -s http://localhost:8000/api/v1/payments/admin/summary/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# ─────────────────────────────────────────────────────────────
# MANUALLY TRIGGER CELERY TASKS (for testing)
# ─────────────────────────────────────────────────────────────

# Trigger daily rent deduction
docker exec yana_payments_celery celery -A payments_service.celery call \
  payments_service.core.tasks.deduct_daily_rent

# Trigger overdue marking
docker exec yana_payments_celery celery -A payments_service.celery call \
  payments_service.core.tasks.mark_overdue_rent_schedules

# Check Celery status
docker exec yana_payments_celery celery -A payments_service.celery inspect active

# ─────────────────────────────────────────────────────────────
# HEALTH CHECKS
# ─────────────────────────────────────────────────────────────
curl -s http://localhost:8004/health/ | jq .
curl -s http://localhost:8000/health/ | jq .
