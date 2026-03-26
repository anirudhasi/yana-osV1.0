# Yana OS — API Testing Guide
# =============================================================
# Base URL: http://localhost:8000  (via Nginx gateway)
# Auth Service direct: http://localhost:8001
# Rider Service direct: http://localhost:8002
# =============================================================

# ─────────────────────────────────────────────────────────────
# STEP 0 — Start the stack
# ─────────────────────────────────────────────────────────────
# cd yana-os
# docker compose up --build

# ─────────────────────────────────────────────────────────────
# PART 1 — AUTH SERVICE
# ─────────────────────────────────────────────────────────────

# 1.1 Admin Login (seeded: admin@yana.in / Admin@123)
curl -s -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yana.in","password":"Admin@123"}' | jq .

# Expected response:
# {
#   "success": true,
#   "data": {
#     "user": { "id": "...", "email": "admin@yana.in", "role": "SUPER_ADMIN" },
#     "tokens": {
#       "access_token": "eyJ...",
#       "refresh_token": "eyJ...",
#       "token_type": "Bearer",
#       "expires_in": 3600
#     }
#   }
# }

# Save the token:
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yana.in","password":"Admin@123"}' | jq -r '.data.tokens.access_token')

echo "Admin token: $ADMIN_TOKEN"

# 1.2 Rider Send OTP
curl -s -X POST http://localhost:8000/api/v1/auth/rider/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210"}' | jq .

# Expected (simulated OTP in logs):
# { "success": true, "data": { "phone": "9876543210", "message": "OTP sent (simulated). For testing use: 123456" } }

# 1.3 Rider Verify OTP (use OTP from logs)
curl -s -X POST http://localhost:8000/api/v1/auth/rider/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","otp":"123456"}' | jq .

RIDER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/rider/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","otp":"123456"}' | jq -r '.data.tokens.access_token')

# 1.4 Get My Profile
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 1.5 Refresh Token
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}" | jq .

# 1.6 Logout
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# ─────────────────────────────────────────────────────────────
# PART 2 — RIDER ONBOARDING FLOW
# ─────────────────────────────────────────────────────────────

# 2.1 Create Rider (admin creates)
curl -s -X POST http://localhost:8000/api/v1/riders/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "full_name": "Rajesh Kumar",
    "phone": "9812345678",
    "email": "rajesh@example.com",
    "preferred_language": "hi",
    "source": "app"
  }' | jq .

# Save rider ID:
RIDER_ID=$(curl -s -X POST http://localhost:8000/api/v1/riders/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"full_name":"Test Rider","phone":"9812340001","preferred_language":"hi"}' \
  | jq -r '.data.id')

echo "Rider ID: $RIDER_ID"

# 2.2 Get Rider Detail
curl -s http://localhost:8000/api/v1/riders/$RIDER_ID/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 2.3 Update Profile
curl -s -X PATCH http://localhost:8000/api/v1/riders/$RIDER_ID/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "full_name": "Rajesh Kumar Updated",
    "date_of_birth": "1995-06-15",
    "gender": "MALE",
    "address_line1": "123 MG Road",
    "city": "Delhi",
    "state": "Delhi",
    "pincode": "110001"
  }' | jq .

# 2.4 Submit KYC Details (encrypted by service)
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/details/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "aadhaar_number": "234567890123",
    "pan_number": "ABCDE1234F",
    "dl_number": "DL1420110012345",
    "dl_expiry_date": "2028-12-31",
    "dl_vehicle_class": "MCWG",
    "bank_account_number": "12345678901234",
    "bank_ifsc": "SBIN0001234",
    "bank_name": "State Bank of India",
    "upi_id": "rajesh@sbi"
  }' | jq .

# Expected: KYC submitted, Celery task queued for verification

# 2.5 Upload Document (multipart form)
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/documents/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "document_type=AADHAAR_FRONT" \
  -F "file=@/path/to/aadhaar_front.jpg" | jq .

# Upload more documents
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/documents/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "document_type=PAN" \
  -F "file=@/path/to/pan_card.jpg" | jq .

curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/documents/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "document_type=DRIVING_LICENSE_FRONT" \
  -F "file=@/path/to/dl_front.jpg" | jq .

# 2.6 List Documents
curl -s http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/documents/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 2.7 Get Onboarding Status (rider app view)
curl -s http://localhost:8000/api/v1/riders/$RIDER_ID/onboarding-status/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 2.8 Admin Approve Per-Document
DOC_ID="<uuid-from-document-list>"
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/documents/$DOC_ID/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"APPROVE"}' | jq .

# 2.9 Admin Reject Per-Document
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/documents/$DOC_ID/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"REJECT","rejection_reason":"Document is blurry. Please re-upload."}' | jq .

# 2.10 Admin Approve Full KYC
# (First, manually set rider to KYC_PENDING/UNDER_REVIEW for testing)
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"APPROVE","notes":"All documents verified successfully"}' | jq .

# 2.11 Admin Reject Full KYC
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/decide/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"REJECT","rejection_reason":"Aadhaar name does not match DL. Please resubmit."}' | jq .

# 2.12 Add Nominee
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/nominees/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "full_name": "Sunita Kumar",
    "relationship": "SPOUSE",
    "phone": "9876500099",
    "is_primary": true
  }' | jq .

# 2.13 Activate Rider (after training)
curl -s -X POST http://localhost:8000/api/v1/riders/$RIDER_ID/activate/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 2.14 View KYC Audit Logs (admin only)
curl -s http://localhost:8000/api/v1/riders/$RIDER_ID/kyc/logs/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# ─────────────────────────────────────────────────────────────
# PART 3 — FILTERING / SEARCH
# ─────────────────────────────────────────────────────────────

# Filter by status
curl -s "http://localhost:8000/api/v1/riders/?status=ACTIVE" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.count'

# Filter by KYC status
curl -s "http://localhost:8000/api/v1/riders/?kyc_status=UNDER_REVIEW" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# Search by name/phone
curl -s "http://localhost:8000/api/v1/riders/?q=Rajesh" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data.results[].full_name'

# Pagination
curl -s "http://localhost:8000/api/v1/riders/?page=2&page_size=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.data | {count, page, total_pages}'

# ─────────────────────────────────────────────────────────────
# PART 4 — HEALTH CHECKS
# ─────────────────────────────────────────────────────────────

curl -s http://localhost:8000/health/ | jq .
curl -s http://localhost:8001/health/ | jq .
curl -s http://localhost:8002/health/ | jq .

# ─────────────────────────────────────────────────────────────
# PART 5 — Swagger UI (browser)
# ─────────────────────────────────────────────────────────────
# Auth service: http://localhost:8001/api/docs/
# Rider service: http://localhost:8002/api/docs/
