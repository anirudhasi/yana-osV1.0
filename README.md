# Yana OS — Backend Foundation

Production-grade monorepo backend for the Yana OS Rider + Fleet + Demand platform.

## Architecture

```
yana-os/
├── api-gateway/           # Nginx reverse proxy config
├── docker/                # DB init scripts
├── docker-compose.yml     # Full local stack
├── services/
│   ├── auth-service/      # Django — Admin JWT + Rider OTP auth
│   └── rider-service/     # Django — Full rider onboarding + KYC
└── shared/
    └── constants/         # Shared enums and constants
```

## Services

| Service       | Port | Tech   | Responsibility                            |
|---------------|------|--------|-------------------------------------------|
| auth-service  | 8001 | Django | Admin JWT login, Rider OTP auth           |
| rider-service | 8002 | Django | Rider onboarding, KYC, document uploads   |
| fleet-service | 8003 | Django | Fleet hubs, vehicles, allotments, alerts  |
| fleet-telemetry | 8013 | FastAPI | GPS telemetry ingestion and live feed   |
| nginx         | 8081 | Nginx  | API gateway, rate limiting, routing       |
| postgres      | 5432 | PG 15  | Primary relational DB                     |
| redis         | 6379 | Redis  | OTP storage, Celery broker, cache         |
| minio         | 9000 | MinIO  | S3-compatible document storage            |

## Quick Start

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- 4GB RAM minimum

### 1. Clone and configure
```bash
git clone <repo>
cd yana-os

# The .env files are pre-configured for local dev.
# In production, change all secrets!
```

### 2. Start the stack
```bash
docker compose up --build
```

Wait for all services to be healthy (~60 seconds on first run).

Note:
- This repo uses gateway port `8081` locally because `8000` was already occupied on this machine by another project.

### 3. Verify services
```bash
curl http://localhost:8001/health/   # auth service
curl http://localhost:8002/health/   # rider service
curl http://localhost:8003/health/   # fleet service
curl http://localhost:8081/health/   # nginx gateway
```

### 4. Seeded admin users
| Email            | Password   | Role        |
|------------------|------------|-------------|
| admin@yana.in    | Admin@123  | SUPER_ADMIN |
| ops@yana.in      | Ops@123    | HUB_OPS     |
| sales@yana.in    | Sales@123  | SALES       |

### 5. API Documentation
- Auth Service:  http://localhost:8001/api/docs/
- Rider Service: http://localhost:8002/api/docs/
- Fleet Service: http://localhost:8003/api/docs/
- Gateway Health: http://localhost:8081/health/
- Demo UI: http://localhost:8081/demo/index.html

### 6. MinIO Console
http://localhost:9001 (user: yana_minio / pass: yana_minio_secret)

---

## API Overview

### Auth Service (via gateway: localhost:8081)

```
POST /api/v1/auth/admin/login         Admin email+password login
POST /api/v1/auth/rider/send-otp      Send OTP to rider phone
POST /api/v1/auth/rider/verify-otp    Verify OTP, get JWT
GET  /api/v1/auth/me                  Get current user profile
POST /api/v1/auth/refresh             Refresh JWT token
POST /api/v1/auth/logout              Invalidate token
```

### Rider Service (via gateway: localhost:8081)

```
POST   /api/v1/riders/                           Create rider
GET    /api/v1/riders/                           List riders (admin)
GET    /api/v1/riders/{id}/                      Get rider detail
PATCH  /api/v1/riders/{id}/profile/              Update profile
POST   /api/v1/riders/{id}/kyc/details/          Submit KYC PII (encrypted)
POST   /api/v1/riders/{id}/kyc/documents/        Upload document file
GET    /api/v1/riders/{id}/kyc/documents/        List documents
POST   /api/v1/riders/{id}/kyc/decide/           Admin: approve/reject KYC
POST   /api/v1/riders/{id}/documents/{d}/decide/ Admin: per-doc decision
GET    /api/v1/riders/{id}/onboarding-status/    Get onboarding progress
POST   /api/v1/riders/{id}/activate/             Admin: activate rider
POST   /api/v1/riders/{id}/nominees/             Add nominee
GET    /api/v1/riders/{id}/nominees/             List nominees
GET    /api/v1/riders/{id}/kyc/logs/             KYC audit trail
```

### Fleet Service (via gateway: localhost:8081)

```
GET    /api/v1/fleet/cities/                              List cities
GET    /api/v1/fleet/hubs/                                List hubs
POST   /api/v1/fleet/hubs/                                Create hub
GET    /api/v1/fleet/hubs/{id}/                           Get hub detail
GET    /api/v1/fleet/hubs/{id}/utilization/               Hub utilization
GET    /api/v1/fleet/vehicles/                            List vehicles
POST   /api/v1/fleet/vehicles/                            Create vehicle
GET    /api/v1/fleet/vehicles/{id}/                       Get vehicle detail
POST   /api/v1/fleet/vehicles/{id}/status/                Update vehicle status
GET    /api/v1/fleet/vehicles/{id}/gps-history/           Vehicle GPS history
GET    /api/v1/fleet/allotments/                          List allotments
POST   /api/v1/fleet/allotments/                          Create allotment
POST   /api/v1/fleet/allotments/{id}/return/              Return vehicle
GET    /api/v1/fleet/alerts/                              List maintenance alerts
POST   /api/v1/fleet/alerts/{id}/acknowledge/             Acknowledge alert
GET    /api/v1/fleet/dashboard/utilization/               Fleet dashboard
POST   /telemetry/ping                                    Single GPS ping
POST   /telemetry/ping/bulk                               Bulk GPS ping
GET    /telemetry/live/{vehicle_id}                       Live vehicle telemetry
GET    /telemetry/fleet/live                              Fleet live positions
```

---

## Rider Onboarding State Machine

```
APPLIED → DOCS_SUBMITTED → KYC_PENDING → VERIFIED → TRAINING → ACTIVE
              ↑                 ↓
              └── KYC_FAILED ←─┘
```

KYC Status:
```
PENDING → SUBMITTED → UNDER_REVIEW → VERIFIED
              ↑              ↓
              └── REJECTED ←─┘
```

---

## Running Tests

```bash
# Auth service
docker exec yana_auth python manage.py test tests --verbosity=2

# Rider service
docker exec yana_rider python manage.py test tests --verbosity=2

# Fleet service
docker exec yana_fleet python manage.py test tests --verbosity=2
```

---

## Local Validation

Validated locally through the gateway:
- `GET http://localhost:8081/health/` returns `200`
- `GET http://localhost:8081/demo/index.html` serves the local browser demo UI
- `POST /api/v1/auth/admin/login` works with `admin@yana.in / Admin@123`
- `POST /api/v1/auth/rider/send-otp` returns a simulated OTP
- `POST /api/v1/auth/rider/verify-otp` returns rider JWT tokens
- Rider-authenticated `GET /api/v1/riders/{id}/onboarding-status/` returns `200`
- Rider access to another rider's onboarding status returns `403`
- Rider access to admin-only `GET /api/v1/riders/` returns `403`

Quick local test flow:
```bash
# 1. Health
curl http://localhost:8081/health/

# 1b. Open the local demo UI in a browser
# http://localhost:8081/demo/index.html

# 2. Admin login
curl -X POST http://localhost:8081/api/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@yana.in\",\"password\":\"Admin@123\"}"

# 3. Rider OTP
curl -X POST http://localhost:8081/api/v1/auth/rider/send-otp \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"9876500001\"}"

# 4. Verify OTP with the 6-digit code from step 3
curl -X POST http://localhost:8081/api/v1/auth/rider/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"9876500001\",\"otp\":\"123456\"}"
```

---

## Demo Deployment

This repo now includes a Render Blueprint:
- [render.yaml](C:\Users\sangi\OneDrive\Documents\Anirudh\Yana\yana-osV1.0\render.yaml)

It provisions:
- public gateway with demo UI
- private `auth-service`
- private `rider-service`
- private MinIO
- Render Postgres
- Render Key Value

After you push to GitHub:
1. Open Render
2. Create a new Blueprint from this repo
3. Select `render.yaml`
4. Apply the Blueprint
5. Once the gateway deploy is live, share that public gateway URL with the client

Client demo URL pattern:
- `https://<render-gateway-url>/demo/index.html`

---

## Celery Worker

The Celery worker (yana_rider_celery) runs automatically with docker compose.

Background tasks:
- `run_kyc_verification(rider_id)` — Auto-verify Aadhaar/PAN/DL/Bank via mock APIs
- `send_kyc_approved_notification(rider_id)` — WhatsApp/Firebase notification stub
- `send_kyc_rejected_notification(rider_id, reason)` — Rejection notification
- `send_activation_notification(rider_id)` — Activation notification
- `trigger_kyc_verification_for_submitted()` — Periodic: process all SUBMITTED riders

Check Celery logs:
```bash
docker logs yana_rider_celery -f
```

---

## Security Notes

### PII Encryption
All sensitive fields (Aadhaar, PAN, DL, bank account) are encrypted using
Fernet symmetric encryption before storage. Set `PII_ENCRYPTION_KEY` in
production (a securely generated 32-byte base64 key).

```bash
# Generate a production PII key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### JWT
Both services share the same `JWT_SECRET_KEY`. In production, rotate this key
regularly and consider moving to RS256 with separate public/private keys.

### OTP
In development, OTPs are logged to stdout (never in production).
Set `OTP_SIMULATE=False` and configure your SMS gateway (Msg91/AWS SNS).

---

## Production Checklist

- [ ] Change all default passwords and secrets in `.env`
- [ ] Set `DEBUG=False`
- [ ] Configure real SMS gateway for OTP
- [ ] Set up AWS KMS / HashiCorp Vault for PII encryption key management
- [ ] Enable HTTPS (SSL/TLS termination at load balancer)
- [ ] Configure Prometheus metrics
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Replace `gunicorn` with `uvicorn` for FastAPI services

---

## Next Services (Phase 2)

- `fleet-service` — Vehicle CRUD, allotment engine, GPS telemetry
- `payments-service` — Double-entry ledger, Razorpay integration, rent schedule
- `marketplace-service` — Demand slots, rider matching, attendance
- `maintenance-service` — Repair logs, cost tracking, alerts
- `skills-service` — Videos, gamification, badges
- `support-service` — Tickets, WhatsApp integration
