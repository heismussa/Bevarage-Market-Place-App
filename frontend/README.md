# BeverageMart frontend

Customer Expo app and store-owner React dashboard, both talking to the Django API.

| App | Stack | Command |
| --- | --- | --- |
| `customer-app` | Expo (React Native) + Expo Router + NativeWind | `npm run dev:customer` |
| `owner-dashboard` | Vite + React + TypeScript + React Router + Tailwind | `npm run dev:owner` |
| `packages/api` | openapi-typescript types, openapi-fetch client, refresh, errors, formatters, labels | used by both apps |
| `packages/ui-tokens` | shared colours, spacing, radius | used by both apps |

Hidden in this version (no UI): store ratings, favourites, opening hours, settings toggles, and card payment. Cash, M-Pesa, Tigo Pesa, and Airtel Money are the checkout methods. Store open/closed is the “Accept new orders” switch.

## Setup

From the repo root, start the API first (`scripts/setup-dev.ps1` on Windows, `scripts/setup-dev.sh` on macOS/Linux). Then:

```bash
cd frontend
npm install
```

Copy env examples (PowerShell):

```powershell
Copy-Item customer-app\.env.example customer-app\.env
Copy-Item owner-dashboard\.env.example owner-dashboard\.env.local
```

On macOS/Linux: `cp customer-app/.env.example customer-app/.env` and `cp owner-dashboard/.env.example owner-dashboard/.env.local`.

`EXPO_PUBLIC_API_URL` / `VITE_API_URL` must point at the API, including `/api/v1`.

- This computer / Expo web: `http://localhost:8000/api/v1`
- Android emulator: `http://10.0.2.2:8000/api/v1`
- Physical phone on the same Wi-Fi: `http://YOUR_LAN_IP:8000/api/v1`

## Run

| App | Command | URL |
| --- | --- | --- |
| Owner dashboard | `npm run dev:owner` | http://localhost:5173 |
| Customer app | `npm run dev:customer` | Expo Dev Tools; press `a` for Android, `w` for web |

Demo phones after `seed_demo` (passwords come from the setup script output / `.env`):

| Who | Phone |
| --- | --- |
| Customer | +255712345002 |
| ABC Drinks owner | +255712345003 |
| Fresh Beverages owner | +255712345004 |

Approve a mock mobile-money payment from the repo root:

```bash
docker compose exec backend python manage.py simulate_mobile_money <transaction_reference>
```

The reset SMS code is in `docker compose logs backend` (look for “SMS to”).

## Scripts

| Script | Purpose |
| --- | --- |
| `npm run gen:api` | Regenerate `packages/api/src/schema.d.ts` from `docs/openapi.yaml` |
| `npm run typecheck` | TypeScript across workspaces |
| `npm run lint` | ESLint |
| `npm run test` | Unit tests (`@beverage/api`) |
| `npm run format` | Prettier |
| `npm run dev:owner` | Owner dashboard on http://localhost:5173 |
| `npm run dev:customer` | Expo for the customer app |
