# Railway + Netlify Deployment

This repo can be deployed without Render by using:

- Railway for backend services
- Netlify for the static demo UI
- Netlify or Vercel for the standalone admin dashboard

## Recommended Public URLs

- Public gateway on Railway
- Optional demo UI on Netlify
- Optional admin dashboard on Netlify or Vercel

If you deploy the gateway publicly on Railway, the simplest setup is:

1. Deploy `auth-service`, `rider-service`, `fleet-service`, `fleet-telemetry`, `payments-service`, `marketplace-service`, `maintenance-service`, `skills-service`, and `support-service` to Railway.
2. Deploy `api-gateway` to Railway with environment-based upstream URLs.
3. Deploy `api-gateway/demo` to Netlify and point it at the Railway gateway URL via `config.js`.
4. Deploy `admin-dashboard` as a static frontend and set `VITE_API_BASE_URL=https://<your-railway-gateway>/api/v1` at build time.

## Railway Services

Create these Railway services from the monorepo:

- `auth-service`
  - Root directory: `services/auth-service`
- `rider-service`
  - Root directory: `services/rider-service`
- `fleet-service`
  - Root directory: `services/fleet-service`
- `fleet-telemetry`
  - Root directory: `services/fleet-service`
- `payments-service`
  - Root directory: `services/payments-service`
- `marketplace-service`
  - Root directory: `services/marketplace-service`
- `maintenance-service`
  - Root directory: `services/maintenance-service`
- `skills-service`
  - Root directory: `services/skills-service`
- `support-service`
  - Root directory: `services/support-service`
- `api-gateway`
  - Root directory: `api-gateway`

Create shared infra in Railway:

- Postgres
- Redis

## Gateway Environment Variables

Set these on the Railway `api-gateway` service:

- `AUTH_SERVICE_URL=https://<public-or-private-auth-url>`
- `RIDER_SERVICE_URL=https://<public-or-private-rider-url>`
- `FLEET_SERVICE_URL=https://<public-or-private-fleet-url>`
- `FLEET_TELEMETRY_URL=https://<public-or-private-telemetry-url>`
- `PAYMENTS_SERVICE_URL=https://<public-or-private-payments-url>`
- `MARKETPLACE_SERVICE_URL=https://<public-or-private-marketplace-url>`
- `MAINTENANCE_SERVICE_URL=https://<public-or-private-maintenance-url>`
- `SKILLS_SERVICE_URL=https://<public-or-private-skills-url>`
- `SUPPORT_SERVICE_URL=https://<public-or-private-support-url>`

If Railway gives you private service domains, use those instead of public URLs.

## Netlify Demo UI

This repo includes:

- `api-gateway/demo/config.js`
- `api-gateway/demo/config.example.js`
- `netlify.toml`

Before deploying to Netlify, update `api-gateway/demo/config.js`:

```js
window.YANA_DEMO_CONFIG = {
  apiBase: "https://your-railway-gateway-url",
};
```

Then deploy the repo to Netlify with:

- Publish directory: `api-gateway/demo`

## Admin Dashboard On Netlify Or Vercel

The `admin-dashboard` app is a Vite static build and is the easiest client-facing UI to host separately.

Recommended build settings:

- Root directory: `admin-dashboard`
- Build command: `npm run build`
- Publish directory: `dist`

Required build environment variable:

```bash
VITE_API_BASE_URL=https://<your-railway-gateway-url>/api/v1
```

Recommended public URL pattern:

- Admin dashboard: `https://<your-admin-site>.netlify.app`

Notes:

- The login screen is `/login`
- After login, the dashboard has routes for `/`, `/riders`, `/fleet`, `/payments`, `/marketplace`, `/maintenance`, `/skills`, and `/support`
- For a clean client demo, keep the Railway gateway public and point the dashboard build to that gateway URL

## Local Default

For local Docker Compose, `config.js` keeps `apiBase` empty, so the demo continues to use same-origin requests through:

- `http://localhost:8081`
