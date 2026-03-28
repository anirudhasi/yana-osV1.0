# Railway + Netlify Deployment

This repo can be deployed without Render by using:

- Railway for backend services
- Netlify for the static demo UI

## Recommended Public URLs

- Public gateway on Railway
- Optional demo UI on Netlify

If you deploy the gateway publicly on Railway, the simplest setup is:

1. Deploy `auth-service`, `rider-service`, `fleet-service`, `fleet-telemetry`, `payments-service`, and `marketplace-service` to Railway.
2. Deploy `api-gateway` to Railway with environment-based upstream URLs.
3. Deploy `api-gateway/demo` to Netlify and point it at the Railway gateway URL via `config.js`.

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

## Local Default

For local Docker Compose, `config.js` keeps `apiBase` empty, so the demo continues to use same-origin requests through:

- `http://localhost:8081`
