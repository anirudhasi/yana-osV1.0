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
| payments-service | 8004 | Django | Wallets, ledger, rent schedules, payments |
| marketplace-service | 8005 | Django | Demand slots, applications, attendance, earnings |
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
curl http://localhost:8004/health/   # payments service
curl http://localhost:8005/health/   # marketplace service
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
- Payments Service: http://localhost:8004/api/docs/
- Marketplace Service: http://localhost:8005/api/docs/
- Gateway Health: http://localhost:8081/health/
- Demo UI: http://localhost:8081/demo/index.html

The demo UI is now configurable for cloud deployment:
- local default config: `api-gateway/demo/config.js`
- example cloud config: `api-gateway/demo/config.example.js`

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

### Payments Service (via gateway: localhost:8081)

```
GET    /api/v1/payments/wallets/{rider_id}/               Wallet summary
GET    /api/v1/payments/wallets/{rider_id}/ledger/        Wallet ledger
POST   /api/v1/payments/wallets/{rider_id}/topup/         Initiate top-up
POST   /api/v1/payments/wallets/{rider_id}/topup/confirm/ Confirm top-up
POST   /api/v1/payments/wallets/{rider_id}/adjust/        Admin wallet adjustment
POST   /api/v1/payments/wallets/{rider_id}/incentive/     Incentive credit
POST   /api/v1/payments/wallets/{rider_id}/upi-mandate/   Create UPI mandate
GET    /api/v1/payments/rent/{rider_id}/schedule/         Rent schedule
GET    /api/v1/payments/rent/{rider_id}/overdue/          Overdue rent items
POST   /api/v1/payments/rent/schedule/create/             Create rent schedule
GET    /api/v1/payments/transactions/{rider_id}/          Transaction history
POST   /api/v1/payments/webhooks/razorpay/                Razorpay webhook
GET    /api/v1/payments/admin/summary/                    Admin payment summary
```

### Marketplace Service (via gateway: localhost:8081)

```
GET    /api/v1/marketplace/clients/                       List clients
POST   /api/v1/marketplace/clients/                       Create client
GET    /api/v1/marketplace/dark-stores/                   List dark stores
POST   /api/v1/marketplace/dark-stores/                   Create dark store
GET    /api/v1/marketplace/demand-slots/                  List demand slots
POST   /api/v1/marketplace/demand-slots/                  Create demand slot
POST   /api/v1/marketplace/demand-slots/{id}/match/       Run rider matching
GET    /api/v1/marketplace/applications/                  List applications
POST   /api/v1/marketplace/applications/                  Apply to a demand slot
POST   /api/v1/marketplace/applications/{id}/shortlist/   Shortlist application
POST   /api/v1/marketplace/applications/{id}/confirm/     Confirm application
GET    /api/v1/marketplace/attendance/                    Attendance list
POST   /api/v1/marketplace/attendance/check-in/           Rider check-in
POST   /api/v1/marketplace/attendance/check-out/          Rider check-out
GET    /api/v1/marketplace/earnings/{rider_id}/           Rider earnings summary
GET    /api/v1/marketplace/admin/summary/                 Admin marketplace summary
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

# Payments service
docker exec yana_payments python manage.py test tests --verbosity=2
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

## Cloud Deployment

### Railway + Netlify

The cleanest cloud fallback for this repo is:
- Railway for backend services
- Railway or Netlify for the demo UI

Files included for that path:
- `RAILWAY.md`
- `netlify.toml`
- `api-gateway/demo/config.js`
- `api-gateway/demo/config.example.js`

Recommended flow:
1. Deploy `auth-service`, `rider-service`, `fleet-service`, `fleet-telemetry`, `payments-service`, and `api-gateway` on Railway.
2. Set the gateway upstream env vars to the Railway service URLs.
3. If you want a separate static client URL, deploy `api-gateway/demo` to Netlify.
4. Point `api-gateway/demo/config.js` at the public Railway gateway URL.

Client demo URL patterns:
- Railway gateway: `https://<railway-gateway-url>/demo/index.html`
- Netlify UI: `https://<netlify-site>.netlify.app`

### Render

This repo still includes a Render Blueprint in `render.yaml`, but Railway + Netlify is the recommended fallback if Render monorepo Docker deployment is unreliable.

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

## DevOps & Kubernetes

### CI/CD Pipeline Overview

**CI (`.github/workflows/ci.yml`)** — triggered on every push and pull request:

1. `lint-and-test` — runs in parallel across all 10 services (matrix strategy). For each service:
   - Builds the Docker image with layer caching (`actions/cache`)
   - Runs the test suite inside the container (`python manage.py test tests --verbosity=2` for Django, `pytest` for FastAPI)
2. `build-and-push` — runs only on `main` branch merges, after tests pass:
   - Logs into GitHub Container Registry (`ghcr.io/yana-os`) using `GITHUB_TOKEN`
   - Builds and pushes each service image tagged as both `ghcr.io/yana-os/<service>:<git-sha>` and `:latest`
   - Includes `admin-dashboard` and `api-gateway` images

**CD (`.github/workflows/cd.yml`)** — triggered when CI completes successfully on `main`:

1. `deploy-staging` — automatically:
   - Pulls kubeconfig from `KUBE_CONFIG_STAGING` secret
   - Updates all deployment images with the new SHA via `kubectl set image`
   - Waits for every rollout with `kubectl rollout status --timeout=300s`
   - Posts a summary to the GitHub Actions step summary
2. `deploy-production` — requires manual approval via the `production` environment:
   - Same rollout process targeting `yana-production` namespace
   - Runs smoke tests (curl `GET /health/` for each service) after deploy

### Deploying to Kubernetes with kubectl

**Prerequisites:** `kubectl` configured for your cluster, secrets created (see below).

```bash
# 1. Create namespaces
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets (fill in real values)
kubectl create secret generic yana-secrets \
  --from-literal=POSTGRES_PASSWORD=<your-pg-password> \
  --from-literal=POSTGRES_USER=yana \
  --from-literal=DJANGO_SECRET_KEY=<your-django-secret> \
  --from-literal=JWT_SECRET_KEY=<your-jwt-secret> \
  --from-literal=PII_ENCRYPTION_KEY=<your-pii-key> \
  --from-literal=MINIO_ACCESS_KEY=<minio-access-key> \
  --from-literal=MINIO_SECRET_KEY=<minio-secret-key> \
  --from-literal=RAZORPAY_KEY_ID=<razorpay-key-id> \
  --from-literal=RAZORPAY_KEY_SECRET=<razorpay-key-secret> \
  -n yana-production

# 3. Create GHCR pull secret
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-pat> \
  -n yana-production

# 4. Apply RBAC, ConfigMap
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/configmap.yaml

# 5. Deploy all services
kubectl apply -f k8s/services/auth-service/
kubectl apply -f k8s/services/rider-service/
kubectl apply -f k8s/services/fleet-service/
kubectl apply -f k8s/services/fleet-telemetry/
kubectl apply -f k8s/services/payments-service/
kubectl apply -f k8s/services/marketplace-service/
kubectl apply -f k8s/services/maintenance-service/
kubectl apply -f k8s/services/skills-service/
kubectl apply -f k8s/services/support-service/
kubectl apply -f k8s/services/api-gateway/

# 6. Deploy Celery workers
kubectl apply -f k8s/celery/

# 7. Apply Ingress
kubectl apply -f k8s/ingress.yaml

# 8. Deploy monitoring
kubectl apply -f k8s/monitoring/prometheus/
kubectl apply -f k8s/monitoring/grafana/

# Update image tags after a new build
kubectl set image deployment/auth-service auth-service=ghcr.io/yana-os/auth-service:<sha> -n yana-production
kubectl rollout status deployment/auth-service -n yana-production
```

### Installing with Helm

```bash
# Install to staging
helm upgrade --install yana-os helm/yana-os \
  -f helm/yana-os/values-staging.yaml \
  --namespace yana-staging \
  --create-namespace \
  --set global.imageTag=<git-sha>

# Install to production
helm upgrade --install yana-os helm/yana-os \
  -f helm/yana-os/values-production.yaml \
  --namespace yana-production \
  --create-namespace \
  --set global.imageTag=<git-sha>

# Check release status
helm status yana-os -n yana-production

# Roll back to previous release
helm rollback yana-os -n yana-production
```

### Accessing Prometheus and Grafana

**Port-forward locally:**

```bash
# Prometheus (http://localhost:9090)
kubectl port-forward svc/prometheus 9090:9090 -n monitoring

# Grafana (http://localhost:3000)
kubectl port-forward svc/grafana 3000:3000 -n monitoring
# Default login: admin / <grafana-admin-password from grafana-secrets>
```

**Via Ingress (after DNS setup):**
- Prometheus: internal only (no public ingress by default — access via port-forward)
- Grafana: `https://grafana.yana.in` (configure a separate Ingress if needed)

**Importing the Yana OS dashboard:**
1. Open Grafana → Dashboards → Import
2. Upload `k8s/monitoring/grafana/dashboards/yana-overview-dashboard.json`
3. Select the `Prometheus` data source
4. Click Import

The dashboard includes: Service Health overview, Request Rate, Error Rate (5xx/4xx), Response Time P95, CPU/Memory by pod, Active Riders gauge, and Wallet Transactions per minute.

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
