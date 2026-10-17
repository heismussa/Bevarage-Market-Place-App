# BeverageMart frontend

Shared foundation for Developer A tasks **A-01 to A-10**.

| App | Stack | Command |
| --- | --- | --- |
| `customer-app` | Expo (React Native) + Expo Router + NativeWind | `npm run dev:customer` |
| `owner-dashboard` | Vite + React + TypeScript + React Router + Tailwind + shadcn-style UI | `npm run dev:owner` |
| `packages/api` | openapi-typescript types, openapi-fetch client, refresh, errors, formatters, labels | used by both apps |
| `packages/ui-tokens` | shared colours, spacing, radius | used by both apps |

## Setup

```bash
cd frontend
npm install
npm run gen:api
```

Copy env examples:

```bash
copy customer-app\.env.example customer-app\.env
copy owner-dashboard\.env.example owner-dashboard\.env.local
```

Start the Django backend first (`scripts/setup-dev.ps1` from the repo root).

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

## What is intentionally not here yet

A-11 (mockup theme polish), A-12+ (full auth state, splash, login, sign-up, addresses, notifications, store profile). Those build on this foundation.
