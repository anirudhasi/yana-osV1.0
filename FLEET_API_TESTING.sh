#!/bin/bash
# Fleet Service API Testing
# =============================================================
# Base URL (via Nginx): http://localhost:8000
# Fleet direct:         http://localhost:8003
# Telemetry direct:     http://localhost:8013
# =============================================================

# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yana.in","password":"Admin@123"}' \
  | jq -r '.data.tokens.access_token')

echo "Token acquired: ${ADMIN_TOKEN:0:20}..."

# ─────────────────────────────────────────────────────────────
# CITIES
# ─────────────────────────────────────────────────────────────
curl -s http://localhost:8000/api/v1/fleet/cities/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data'

# ─────────────────────────────────────────────────────────────
# HUBS
# ─────────────────────────────────────────────────────────────

# List hubs
curl -s http://localhost:8000/api/v1/fleet/hubs/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].name'

# Create hub
HUB_ID=$(curl -s -X POST http://localhost:8000/api/v1/fleet/hubs/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "city_id":   "11111111-0000-0000-0000-000000000001",
    "name":      "Delhi East Hub",
    "address":   "Patparganj, East Delhi",
    "latitude":  28.6262,
    "longitude": 77.2946,
    "capacity":  30
  }' | jq -r '.data.id')
echo "Created hub: $HUB_ID"

# Hub utilization
curl -s http://localhost:8000/api/v1/fleet/hubs/$HUB_ID/utilization/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# ─────────────────────────────────────────────────────────────
# VEHICLES
# ─────────────────────────────────────────────────────────────

# List vehicles (seeded: 20 vehicles)
curl -s "http://localhost:8000/api/v1/fleet/vehicles/?page_size=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {count, total_pages}'

# Filter by status
curl -s "http://localhost:8000/api/v1/fleet/vehicles/?status=AVAILABLE" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Filter by hub
curl -s "http://localhost:8000/api/v1/fleet/vehicles/?hub_id=22222222-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].registration_number'

# Search by reg
curl -s "http://localhost:8000/api/v1/fleet/vehicles/?q=DL01" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].registration_number'

# Create vehicle
VEHICLE_ID=$(curl -s -X POST http://localhost:8000/api/v1/fleet/vehicles/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "hub_id":               "22222222-0000-0000-0000-000000000001",
    "registration_number":  "DL01ZZ9999",
    "make":                 "Ather",
    "model":                "450X",
    "manufacturing_year":   2024,
    "color":                "Space Grey",
    "battery_capacity_kwh": 2.9,
    "range_km":             85,
    "max_speed_kmh":        90,
    "purchase_price":       145000,
    "purchase_date":        "2024-01-01",
    "insurance_expiry":     "2026-01-01",
    "puc_expiry":           "2025-12-31",
    "fitness_expiry":       "2026-06-30",
    "next_service_km":      5000,
    "next_service_date":    "2025-07-01"
  }' | jq -r '.data.id')
echo "Created vehicle: $VEHICLE_ID"

# Get vehicle detail
curl -s http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {registration_number, status, needs_service}'

# Update vehicle
curl -s -X PATCH http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"battery_level_pct": 85, "is_charging": false}' | jq '.data.battery_level_pct'

# Change status to MAINTENANCE
curl -s -X POST http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"status":"MAINTENANCE","reason":"Scheduled 5000km service"}' | jq .

# Change back to AVAILABLE
curl -s -X POST http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"status":"AVAILABLE","reason":"Service complete"}' | jq .

# ─────────────────────────────────────────────────────────────
# ALLOTMENTS
# ─────────────────────────────────────────────────────────────

# Create allotment (allocate vehicle to rider)
RIDER_ID="<replace-with-real-rider-uuid>"

ALLOTMENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/fleet/allotments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"rider_id\":          \"$RIDER_ID\",
    \"vehicle_id\":        \"$VEHICLE_ID\",
    \"daily_rent_amount\": 150,
    \"security_deposit\":  1000,
    \"condition_at_allotment\": \"Good — no visible damage\"
  }" | jq -r '.data.id')
echo "Created allotment: $ALLOTMENT_ID"

# List allotments
curl -s "http://localhost:8000/api/v1/fleet/allotments/?status=ACTIVE" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Get allotment detail
curl -s http://localhost:8000/api/v1/fleet/allotments/$ALLOTMENT_ID/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {status, daily_rent_amount}'

# Return vehicle
curl -s -X POST http://localhost:8000/api/v1/fleet/allotments/$ALLOTMENT_ID/return/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "odometer_at_return":    1450,
    "battery_pct_at_return": 62,
    "condition_at_return":   "Good",
    "damage_notes":          "",
    "refund_deposit":        true,
    "return_type":           "RETURNED"
  }' | jq '.data | {status, km_driven}'

# Vehicle allotment history
curl -s http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/allotments/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].status'

# ─────────────────────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────────────────────

# List unresolved alerts
curl -s "http://localhost:8000/api/v1/fleet/alerts/?unresolved=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Filter by severity
curl -s "http://localhost:8000/api/v1/fleet/alerts/?severity=HIGH" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].alert_type'

# Acknowledge alert
ALERT_ID="<replace-with-alert-uuid>"
curl -s -X POST http://localhost:8000/api/v1/fleet/alerts/$ALERT_ID/acknowledge/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.is_acknowledged'

# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

curl -s http://localhost:8000/api/v1/fleet/dashboard/utilization/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.summary'

# Filter dashboard by city
curl -s "http://localhost:8000/api/v1/fleet/dashboard/utilization/?city_id=11111111-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.hubs[].hub_name'

# ─────────────────────────────────────────────────────────────
# GPS TELEMETRY (FastAPI on port 8013 or via gateway /telemetry/)
# ─────────────────────────────────────────────────────────────

# Single GPS ping
curl -s -X POST http://localhost:8013/telemetry/ping \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"vehicle_id\":  \"$VEHICLE_ID\",
    \"latitude\":    28.6139,
    \"longitude\":   77.2090,
    \"speed_kmh\":   35.5,
    \"battery_pct\": 72.0,
    \"odometer_km\": 1460
  }" | jq .

# Bulk GPS pings (offline sync)
curl -s -X POST http://localhost:8013/telemetry/ping/bulk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"pings\": [
      {\"vehicle_id\":\"$VEHICLE_ID\",\"latitude\":28.6140,\"longitude\":77.2092,\"speed_kmh\":30,\"battery_pct\":71},
      {\"vehicle_id\":\"$VEHICLE_ID\",\"latitude\":28.6145,\"longitude\":77.2100,\"speed_kmh\":28,\"battery_pct\":70},
      {\"vehicle_id\":\"$VEHICLE_ID\",\"latitude\":28.6150,\"longitude\":77.2108,\"speed_kmh\":0,\"battery_pct\":70}
    ]
  }" | jq '{accepted, buffered}'

# Get live position (Redis → Postgres fallback)
curl -s http://localhost:8013/telemetry/live/$VEHICLE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# Fleet-wide live positions
curl -s http://localhost:8013/telemetry/fleet/live \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '{count: .count}'

# GPS history (Django endpoint)
curl -s "http://localhost:8000/api/v1/fleet/vehicles/$VEHICLE_ID/gps-history/?limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq 'length'

# ─────────────────────────────────────────────────────────────
# WebSocket — connect in browser or wscat
# npm install -g wscat
# ─────────────────────────────────────────────────────────────
# wscat -c "ws://localhost:8000/ws/vehicle/$VEHICLE_ID" \
#   -H "Authorization: Bearer $ADMIN_TOKEN"
#
# wscat -c "ws://localhost:8000/ws/fleet" \
#   -H "Authorization: Bearer $ADMIN_TOKEN"

# Telemetry health
curl -s http://localhost:8013/health | jq .
