# Yana OS — Admin Dashboard

Production React admin dashboard for Yana OS, connecting to all 8 backend microservices.

## Tech Stack

- **React 18** + **Vite 5**
- **TailwindCSS 3** — utility-first styling with custom Yana design tokens
- **Recharts 2** — AreaChart, BarChart, LineChart, PieChart for all metrics
- **TanStack Table v8** — sortable, filterable, paginated rider table
- **React Router v6** — SPA routing with auth guard
- **Axios** — API client with JWT interceptors
- **date-fns** — date formatting throughout

## Pages

| Route | Page | Key Charts |
|-------|------|-----------|
| `/` | Dashboard | Revenue area chart, fleet donut, hub utilization, demand timeline |
| `/riders` | Riders | Growth bar chart, status pie, TanStack Table (sort/filter/paginate) |
| `/fleet` | Fleet & Vehicles | Hub utilization bar chart, fleet status donut, utilization trend |
| `/payments` | Payments | 30-day revenue area chart, collection efficiency, overdue analysis |
| `/marketplace` | Marketplace | Fill rate heatmap table, demand vs actual timeline, shift distribution |
| `/maintenance` | Maintenance | Stacked cost bar chart, alert breakdown, cost per hub |
| `/skills` | Skills & Gamification | Module completion bars, leaderboard, badge distribution, levels |
| `/support` | Support & Tickets | Recent tickets table, SLA performance, category breakdown |

## Quick Start (Dev)

```bash
cd admin-dashboard
npm install
npm run dev
# Open http://localhost:3000
# Uses the repo gateway at http://localhost:8081
# Login: admin@yana.in / Admin@123
```

## Production Build + Docker

```bash
# Build the static production bundle first
npm run build

# Build container
docker build -t yana-admin-dashboard .

# Run on the same Docker network as the repo gateway container
docker run -p 3000:80 yana-admin-dashboard
```

The Docker image in this repo now serves the prebuilt `dist/` output directly.
That means `docker compose --profile ui up -d --build` uses the offline/static image flow by default.
When dashboard source files change, rerun:

```bash
npm run build
```

## Cloud Demo Deployment

For the fastest client demo, deploy the backend gateway on Railway and the admin dashboard as a static site on Netlify or Vercel.

Recommended settings:

```bash
Root directory: admin-dashboard
Build command: npm run build
Publish directory: dist
```

Required build environment variable:

```bash
VITE_API_BASE_URL=https://<your-public-gateway>/api/v1
```

After deployment, the client-facing routes are:

- `/login`
- `/`
- `/riders`
- `/fleet`
- `/payments`
- `/marketplace`
- `/maintenance`
- `/skills`
- `/support`

In this repo, docker-compose already includes:
```yaml
admin-dashboard:
  build: ./admin-dashboard
  container_name: yana_admin_dashboard
  ports: ["3000:80"]
  depends_on: [nginx]
```

## Connecting to Real Backend

The mock data in `src/api/mockData.js` mirrors the backend schema exactly.
To switch to real API calls:

1. Set `VITE_API_BASE_URL` in `.env.local`:
```
VITE_API_BASE_URL=http://localhost:8081/api/v1
```

2. In each page, replace mock data imports with API calls:
```js
// Before (mock):
import { revenueData } from '../api/mockData'

// After (real):
import { paymentsApi } from '../api/client'
const [data, setData] = useState([])
useEffect(() => { paymentsApi.summary().then(res => setData(res.data)) }, [])
```

All API endpoints are defined in `src/api/client.js`.

## Design System

Custom design tokens in `tailwind.config.js`:
- `brand` — Yana green (primary actions, positive states)
- `surface` — Neutral grays (backgrounds, borders, text)
- `accent.amber` — Warnings
- `accent.red` — Errors, overdue
- `accent.blue` — Info, fleet

Typography:
- **Syne** — Display headings (stat numbers, page titles)
- **DM Sans** — Body text, labels
- **JetBrains Mono** — Numbers, codes, amounts
