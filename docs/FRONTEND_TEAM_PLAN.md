# Frontend team plan (3 developers)

This plan takes three developers from a fresh clone to the two products in the mockups:

- **Customer mobile app** (dark theme): splash, home, store page, product detail, cart,
  checkout, order tracking, profile.
- **Store owner dashboard** (web, dark and light themes): dashboard, orders, order
  detail, products, add/edit product, low-stock alerts, sales analytics, store profile.

The backend is finished and is the single source of truth. Read
[`FRONTEND_HANDOFF.md`](FRONTEND_HANDOFF.md) before writing any screen. The contract is
[`openapi.yaml`](openapi.yaml).

---

## 1. Recommended stack

| Part | Choice | Why |
| --- | --- | --- |
| Customer app | Expo (React Native) + TypeScript + Expo Router | One codebase for Android and iOS; the mockups are phone screens. |
| Owner dashboard | React + Vite + TypeScript + React Router | The mockups are a desktop web layout with a sidebar. |
| Styling | Customer: NativeWind (Tailwind for React Native). Owner: Tailwind CSS + shadcn/ui | Same design tokens (colours, spacing) in both apps; shadcn gives tables, dialogs and a theme switch. |
| Server data | TanStack Query in both apps | Caching, retries, and the polling the backend relies on (`refetchInterval`). |
| API client | `openapi-typescript` + `openapi-fetch`, in a shared package | Types come from `docs/openapi.yaml`, so a backend change breaks the build instead of the screen. |
| Forms | react-hook-form + zod | Server field errors map straight onto form fields. |
| Charts | Recharts (owner) | Daily sales line, top products bars. |
| Token storage | Customer: `expo-secure-store`. Owner: memory + `localStorage` for the refresh token | Never store the password. |

Everything is TypeScript. Use npm workspaces so both apps share one API package.

### Folder layout

```
frontend/
  package.json              npm workspaces root
  packages/
    api/                    shared: generated types, client, auth refresh, errors, formatters
      src/schema.d.ts       generated from docs/openapi.yaml (do not edit by hand)
      src/client.ts         openapi-fetch client + token refresh middleware
      src/errors.ts         ApiError type, code -> message map, field error helper
      src/format.ts         money "1500.00" -> "TSh 1,500", dates in Africa/Dar_es_Salaam
      src/labels.ts         order status and payment status labels (handoff section 3)
    ui-tokens/              colours, radius, spacing for dark and light themes
  customer-app/             Expo app
  owner-dashboard/          Vite app
```

---

## 2. Day one: from clone to a running backend (everyone)

1. Clone the repository and install Docker Desktop and Node.js 20 LTS.
2. Create the backend environment file. Get the demo passwords and the mock payment
   secret from the backend owner **privately** (never in chat groups or commits).

   ```powershell
   Copy-Item .env.example .env
   ```

3. Allow the frontends to reach the API. In `.env`:

   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,backend,10.0.2.2,192.168.1.50
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8081
   ```

   - `5173` is the Vite dashboard and `8081` is Expo web.
   - `10.0.2.2` is how the Android emulator reaches your computer.
   - Replace `192.168.1.50` with your computer's Wi-Fi IP (`ipconfig`) so a real phone
     running Expo Go can reach the API. The phone and computer must be on the same Wi-Fi.
   - Native mobile requests do not need CORS; only the browser does.

4. Start and seed the backend:

   ```powershell
   docker compose up --build -d
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py seed_demo
   ```

5. Open <http://localhost:8000/api/docs/>, log in as the demo customer with
   `POST /api/v1/auth/login/`, and try `GET /api/v1/stores/`. If that works, the backend
   is ready.
6. Useful backend commands while building screens:

   | Need | Command |
   | --- | --- |
   | See a password reset code | `docker compose logs backend` (look for "SMS to") |
   | Approve a mobile-money payment | `docker compose exec backend python manage.py simulate_mobile_money <transaction_reference>` |
   | Decline it | add `--fail` to the command above |
   | Reset to clean demo data | `docker compose down -v`, then steps 4 again |

---

## 3. Who does what

Each developer owns whole screens end to end (UI, API calls, loading, empty and error
states). Nobody waits for anyone after week 1.

### Developer A: foundation, accounts and notifications

Owns the shared code that the other two depend on, so A starts first.

**Week 1 (blocking, finish by day 3):**

- `frontend/` workspace, both empty apps booting, ESLint + Prettier + TypeScript strict.
- `packages/api`: generated types, typed client, base URL from env
  (`EXPO_PUBLIC_API_URL`, `VITE_API_URL`), token refresh on `401 TOKEN_INVALID`
  (refresh once, retry once, else log out), error helper, money/date formatters,
  status label maps.
- `packages/ui-tokens`: dark and light palettes from the mockups.
- Auth state for both apps: `GET auth/me/` on start, route by `role`
  (CUSTOMER to the app, STORE_OWNER to the dashboard, others see "not supported").

**Customer app screens:**

- Splash, Log in, Sign up (role CUSTOMER), Forgot password (phone, then code + new
  password), Profile (edit name/phone/email), Change password, Log out.
- Addresses: list, add, edit, delete, set default. Device location for `lat`/`lng`.
- Notifications: bell with unread count (poll 30-60 s), list, mark read, mark all read.
  Tapping an order notification opens that order.

**Owner dashboard screens:**

- Log in, Sign up (role STORE_OWNER), Forgot password, Change password.
- Top bar: bell, notifications dropdown, profile menu, dark/light theme switch.
- Store Profile: create the first store (an owner with no store lands here), edit
  details, logo upload, OPEN/CLOSED switch ("Accept new orders").

### Developer B: customer shopping and ordering

**Screens:**

- Home: location chip, search bar (searches stores), category chips, nearby stores
  sorted by distance, open/closed badge.
- Store page: header, product search, category filter, product grid, add to cart.
- Product detail: image, price, stock, quantity stepper, Add to cart.
- Cart: lines, quantity changes, remove, `warnings`, the "start a new cart" dialog for
  `CART_STORE_CONFLICT`, subtotal.
- Checkout: delivery address picker (from Developer A's addresses), payment method
  (Cash, M-Pesa, Tigo Pesa, Airtel Money), notes, totals from the server, Place order.
- Payment: for mobile money call `pay/`, then poll `payment/` every 3 s for up to
  2 minutes; success, failed with retry, and "not charged" states.
- Order tracking: status timeline from `status_history`, items, totals, payment status,
  poll every 15-30 s until final, Cancel while PENDING (with reason).
- My orders: list with status filter, pagination, open detail.

### Developer C: store owner dashboard

**Screens:**

- Layout: sidebar (Dashboard, Orders, Products, Low stock, Sales Analytics, Store
  Profile), store switcher if the owner has more than one store, responsive down to
  tablet.
- Dashboard (`owner/stores/{id}/dashboard/`): total orders, total sales, pending count,
  7-day sales chart, recent orders, low-stock card. For "today" figures or top products,
  call `owner/stores/{id}/analytics/` with today's or this week's dates. Poll PENDING
  orders every 15-30 s.
- Orders: tabs or filter by status, search, date range, pagination, client-side CSV
  export of the loaded rows.
- Order detail: customer, address, items, totals, payment status, history timeline,
  action buttons only from `allowed_actions`, reason dialog for reject and cancel.
- Products: table with image, price, stock, availability, search, category filter,
  `?low_stock=true` view (the "Inventory" / "Low stock alerts" page).
- Add/Edit product: form, image upload under 2 MB, category, price, stock,
  low-stock threshold, availability; quick stock update; soft delete.
- Sales analytics: date range picker, totals, daily sales line, top products.
  "This week vs last week" = two analytics calls.

### Shared ownership rules

- Only Developer A edits `packages/api` and `packages/ui-tokens`. Others open a small PR
  or ask A.
- Nobody edits the backend. Backend questions go to the backend owner with the exact
  request, response and `error.code`.
- After any backend change: pull, then `npm run gen:api` in `frontend/` (runs
  `openapi-typescript ../docs/openapi.yaml -o packages/api/src/schema.d.ts`).

---

## 4. Timeline (5 weeks)

| Week | Developer A | Developer B | Developer C |
| --- | --- | --- | --- |
| 1 | Workspace, `packages/api`, tokens, auth routing (done by day 3); login and sign-up screens | Static UI for home, store page, product detail using mock JSON from the handoff | Dashboard layout, sidebar, theme switch, static dashboard and orders screens |
| 2 | Forgot/change password, profile, addresses | Connect home, store, product to the API; cart | Connect orders list and detail, transitions |
| 3 | Notifications in both apps; store profile and store creation | Checkout, payment polling, order tracking | Products list, add/edit, stock, low stock |
| 4 | Help B and C; empty/error states review across both apps | My orders, cancel, edge cases (closed store, out of stock, conflicts) | Dashboard data, analytics charts, export |
| 5 | Everyone: end-to-end demo run, bug fixing, dark/light polish, build the Android APK and the dashboard production build |

Have a 15-minute check-in every day and a demo every Friday on the seeded data.

---

## 5. Git workflow

- `main` always runs. Nobody pushes to `main` directly.
- Branch per feature: `feat/customer-cart`, `feat/owner-orders`, `fix/refresh-loop`.
- Small pull requests (one screen or one flow). Another developer reviews before merge.
- Conventional commit messages: `feat(customer): add cart screen`.
- Never commit `.env` files, demo passwords, tokens, or the payment secret.
  Frontend env files hold only the API URL; commit an `.env.example` for each app.
- Pull `main` every morning; rerun `npm run gen:api` when `docs/openapi.yaml` changed.

---

## 6. Definition of done for a screen

- Uses generated types; no hand-written response types.
- Has loading, empty, error and success states.
- Handles every `error.code` the endpoint lists (see the handoff error table); field
  errors appear under the right input.
- Never calculates prices, totals or statuses; shows the server values.
- Buttons that call the API are disabled while the request is in flight.
- Works in dark mode (owner dashboard also in light mode).
- Checked against the mockup and the handoff "must / must not" list.

---

## 7. Final demo script (matches the mockups)

1. Owner signs up on the dashboard, creates a store, uploads a logo, adds products.
2. Customer signs up on the phone, allows location, sees the store on Home, opens it,
   adds two products, checks out with M-Pesa.
3. Run `simulate_mobile_money`; the payment screen turns to "Paid".
4. The owner's bell shows a new order; the dashboard pending count goes up.
5. Owner accepts, prepares, marks ready, completes. The customer's tracking screen
   follows each step and the bell shows each update.
6. Stock drops; a low-stock alert appears when a product reaches its threshold.
7. Dashboard and analytics show the sale.
8. Customer uses Forgot password; the code comes from the backend log.

---

## 8. Mockup items the backend does not provide yet

Build the screens without these, or as described in section 5 of the handoff. The
backend can add the items marked "no schema change" quickly on request.

| Mockup item | Today | Backend option |
| --- | --- | --- |
| Store rating "4.5 (120)" | Hide | Needs new tables (schema change) |
| Favourite heart | Hide | Needs a new table (schema change) |
| Opening hours | Show OPEN/CLOSED | Needs new columns (schema change) |
| Card payment | Hide | Needs a card gateway |
| "Popular products" on home | Show stores | Public top-products endpoint (no schema change) |
| "+12% vs last week" | Compute from two analytics calls, or hide | Comparison in the dashboard response (no schema change) |
| Payment methods donut chart | Hide | Breakdown by method in analytics (no schema change) |
| Orders Export | Client-side CSV | CSV endpoint (no schema change) |
| Notifications / low-stock toggles in Settings | Hide | Needs new columns (schema change) |
| One search for orders, products, customers | Per-page search | Combined search endpoint (no schema change) |
