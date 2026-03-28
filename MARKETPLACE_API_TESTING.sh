#!/bin/bash
# =============================================================
# Yana OS — Marketplace Service API Testing
# Marketplace Service: http://localhost:8005
# Via gateway:         http://localhost:8000/api/v1/marketplace/
# =============================================================

ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yana.in","password":"Admin@123"}' | jq -r '.data.tokens.access_token')

echo "Token: ${ADMIN_TOKEN:0:30}..."

# ─────────────────────────────────────────────────────────────
# CLIENTS (seeded: Blinkit, BigBasket, JioMart)
# ─────────────────────────────────────────────────────────────
curl -s http://localhost:8000/api/v1/marketplace/clients/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].name'

# Create a new client
CLIENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/marketplace/clients/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name":"Zepto","category":"quick_commerce","primary_contact_name":"Zepto Ops","primary_contact_email":"ops@zepto.com"}' \
  | jq -r '.data.id')
echo "Created client: $CLIENT_ID"

# Create dark store for Zepto
STORE_ID=$(curl -s -X POST http://localhost:8000/api/v1/marketplace/clients/$CLIENT_ID/dark-stores/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "city_id":   "11111111-0000-0000-0000-000000000001",
    "hub_id":    "22222222-0000-0000-0000-000000000001",
    "name":      "Zepto Rohini",
    "address":   "Sector 10, Rohini, Delhi",
    "latitude":  "28.7200",
    "longitude": "77.1050"
  }' | jq -r '.data.id')
echo "Created dark store: $STORE_ID"

# Create contract
curl -s -X POST http://localhost:8000/api/v1/marketplace/clients/$CLIENT_ID/contracts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"dark_store_id\":   \"$STORE_ID\",
    \"contract_start\":  \"$(date +%Y-%m-%d)\",
    \"pay_per_order\":   \"40.00\"
  }" | jq '.data | {id, pay_per_order}'

# ─────────────────────────────────────────────────────────────
# DEMAND SLOTS
# ─────────────────────────────────────────────────────────────

# List all slots (admin sees all)
curl -s "http://localhost:8000/api/v1/marketplace/slots/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {count, statuses: [.results[].status]}'

# Filter published only
curl -s "http://localhost:8000/api/v1/marketplace/slots/?status=PUBLISHED" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Filter by client
curl -s "http://localhost:8000/api/v1/marketplace/slots/?client_id=aaaaaaaa-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].title'

# Create a new demand slot
TOMORROW=$(date -d "+1 day" +%Y-%m-%d 2>/dev/null || date -v+1d +%Y-%m-%d)
SLOT_ID=$(curl -s -X POST http://localhost:8000/api/v1/marketplace/slots/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"client_id\":       \"$CLIENT_ID\",
    \"dark_store_id\":   \"$STORE_ID\",
    \"city_id\":         \"11111111-0000-0000-0000-000000000001\",
    \"title\":           \"Zepto Rohini — Morning Shift\",
    \"shift_type\":      \"MORNING\",
    \"shift_date\":      \"$TOMORROW\",
    \"shift_start_time\":\"06:00:00\",
    \"shift_end_time\":  \"14:00:00\",
    \"shift_duration_hrs\": 8.0,
    \"riders_required\": 5,
    \"pay_structure\":   \"PER_ORDER\",
    \"pay_per_order\":   \"40.00\",
    \"earnings_estimate\": \"800.00\",
    \"vehicle_required\": true
  }" | jq -r '.data.id')
echo "Created slot: $SLOT_ID"

# Publish slot (triggers matching engine)
curl -s -X POST http://localhost:8000/api/v1/marketplace/slots/$SLOT_ID/publish/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {status, title}'

# Get matching results (after brief pause for Celery)
sleep 3
curl -s http://localhost:8000/api/v1/marketplace/slots/$SLOT_ID/matches/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {match_count}'

# ─────────────────────────────────────────────────────────────
# RIDER APPLICATION FLOW
# ─────────────────────────────────────────────────────────────
RIDER_ID="<paste-rider-uuid-from-seed-data>"
RIDER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/rider/send-otp \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"9876500001\"}" | jq -r '.data.message' | grep -o '[0-9]\{6\}')
# Verify OTP and get token
# RIDER_TOKEN=...

# Rider views published slots
curl -s "http://localhost:8000/api/v1/marketplace/slots/" \
  -H "Authorization: Bearer $RIDER_TOKEN" | jq '.data | {count, slots: [.results[] | {title, shift_date, earnings_estimate}]}'

# Rider applies for a seeded slot
BLINKIT_SLOT=$(curl -s "http://localhost:8000/api/v1/marketplace/slots/?status=PUBLISHED" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.data.results[0].id')

APP_ID=$(curl -s -X POST http://localhost:8000/api/v1/marketplace/slots/$BLINKIT_SLOT/apply/ \
  -H "Authorization: Bearer $RIDER_TOKEN" | jq -r '.data.id')
echo "Application ID: $APP_ID"

# Admin shortlists
curl -s -X POST http://localhost:8000/api/v1/marketplace/applications/$APP_ID/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"SHORTLIST"}' | jq '.data.status'

# Admin confirms
curl -s -X POST http://localhost:8000/api/v1/marketplace/applications/$APP_ID/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"CONFIRM"}' | jq '.data.status'

# Rider checks in (morning of shift)
curl -s -X POST http://localhost:8000/api/v1/marketplace/applications/$APP_ID/check-in/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RIDER_TOKEN" \
  -d '{"latitude":"28.7200","longitude":"77.1050"}' | jq '.data | {message, check_in_at}'

# Rider checks out (end of shift)
curl -s -X POST http://localhost:8000/api/v1/marketplace/applications/$APP_ID/check-out/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RIDER_TOKEN" \
  -d '{"latitude":"28.7200","longitude":"77.1050","orders_completed":22}' \
  | jq '.data | {message, hours_worked, orders_completed, estimated_earnings}'

# ─────────────────────────────────────────────────────────────
# BULK OPERATIONS
# ─────────────────────────────────────────────────────────────

# Bulk confirm top matches
curl -s -X POST http://localhost:8000/api/v1/marketplace/slots/$SLOT_ID/bulk-confirm/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"count":5}' | jq '.data | {confirmed_count, slot_fill_rate}'

# Payout all completed applications
curl -s -X POST http://localhost:8000/api/v1/marketplace/slots/$BLINKIT_SLOT/payout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"application_ids\":[\"$APP_ID\"]}" | jq '.data | {paid, failed}'

# ─────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────

# Fill rate report
curl -s "http://localhost:8000/api/v1/marketplace/analytics/fill-rates/?days=7" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {count, slots: [.slots[] | {title, fill_rate, show_up_rate}]}'

# Fill rate by city
curl -s "http://localhost:8000/api/v1/marketplace/analytics/fill-rates/?city_id=11111111-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Dashboard
curl -s http://localhost:8000/api/v1/marketplace/analytics/dashboard/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {slots, top_clients: [.top_clients[] | {name, total_slots}]}'

# ─────────────────────────────────────────────────────────────
# RIDER'S OWN APPLICATION HISTORY
# ─────────────────────────────────────────────────────────────
curl -s "http://localhost:8000/api/v1/marketplace/riders/$RIDER_ID/applications/" \
  -H "Authorization: Bearer $RIDER_TOKEN" | jq '.data | {count, statuses: [.results[].status]}'

# Filter by status
curl -s "http://localhost:8000/api/v1/marketplace/riders/$RIDER_ID/applications/?status=COMPLETED" \
  -H "Authorization: Bearer $RIDER_TOKEN" | jq '.data.results[].earnings_credited'

# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────
curl -s http://localhost:8005/health/ | jq .
