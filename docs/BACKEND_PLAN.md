# Backend plan: Stages 0-7

This is the working plan for the Django REST backend. The database schema in
`docs/erd/beverage_delivery_erd_v2_1.dbml` is the source of truth; this plan only
describes the API and business rules built on top of it.

## Status

| Stage | Scope | Status |
|---|---|---|
| 0 | Shared plumbing | Done |
| 1 | Store and product APIs | Done |
| 2 | Addresses and cart | Done |
| 3 | Orders and state machine | Done |
| 4 | Store order management and dashboard | Done |
| 5 | Payments | Done |
| 6 | Notifications (in-app only) | Done |
| 7 | Frontend handoff | Not started |

## Global rules (apply to every stage)

1. **Schema.** The DBML is the source of truth. Do not add, rename or remove tables or
   fields. If the schema must change, stop and ask first. Computed, read-only serializer
   fields are allowed.
2. **Thin views.** Business logic lives in each app's `services.py` (and
   `orders/state_machine.py`). Serializers only validate and shape data.
3. **Money.** Decimal only. Recompute every price and total on the server. Never trust
   prices, totals or statuses sent by the client.
4. **Permissions.** Default deny. Use the role classes in `accounts/permissions.py`.
   Owners touch only their own stores' data; customers only their own cart, addresses,
   orders and notifications. Return 404 (not 403) for objects the user may not see.
5. **Errors.** One format via the custom DRF exception handler:
   `{"error": {"code": "SOME_CODE", "message": "...", "details": {}}}`.
   Codes are stable and machine-readable.
6. **Lists.** Paginated (default 20, max 100), filterable with django-filter, optimised
   with `select_related`/`prefetch_related`, and covered by a query-count test.
7. **Docs.** Every endpoint uses `extend_schema` (request, response, error responses,
   examples) and is tagged by area.
8. **Time.** `TIME_ZONE = "Africa/Dar_es_Salaam"`, `USE_TZ = True`.
9. **Tests.** Required in every stage. Money, stock and state logic need unit tests and
   API tests.
10. **Out of scope.** Driver/Delivery models, WebSockets, SMS/push, frontend code,
    secrets in the repository.
11. **End of every stage.** Run the tests, `makemigrations --check --dry-run` and ruff,
    then report and wait for "proceed to Stage N".
12. **Git.** The developer commits and pushes manually. No tool or AI attribution in
    any commit.

## Stage 0: Shared plumbing

- Custom exception handler, error code module and pagination class.
- Ownership and permission helpers; factory_boy factories for every model.
- Test helpers: authenticated API client per role (customer, store owner, admin).
- Ruff config. README section describing these conventions.

Done when a sample endpoint test uses the helpers and the error format works.

## Stage 1: Store and product APIs

Public (read-only, no login):

- `GET /api/v1/categories/`
- `GET /api/v1/stores/`: active stores only; filters `status`, `city`, `area`,
  `search`, `category`. Optional `?lat=&lng=` adds `distance_km` (Haversine) and
  allows `ordering=distance`.
- `GET /api/v1/stores/{id}/`
- `GET /api/v1/stores/{id}/products/`: excludes soft-deleted; filters `category`,
  `search`, `availability`, `in_stock`; ordering by name or price.
- `GET /api/v1/products/{id}/`

Store owner:

- `GET, POST /api/v1/owner/stores/`
- `GET, PATCH /api/v1/owner/stores/{id}/`: owners cannot change `is_active`.
- `GET, POST /api/v1/owner/stores/{store_id}/products/`: filters `low_stock`,
  `availability`, `search`.
- `GET, PATCH, DELETE /api/v1/owner/products/{id}/`: DELETE sets `deleted_at`.
- `PATCH /api/v1/owner/products/{id}/stock/`

Rules:

- Availability sync: stock 0 makes a product OUT_OF_STOCK; stock above 0 on an
  OUT_OF_STOCK product makes it AVAILABLE. UNAVAILABLE is set and cleared only by the
  owner: stock changes (including orders and restocks) never change it.
- Images: JPEG, PNG or WebP, max 2 MB, checked with Pillow. Price > 0. Category must
  be ACTIVE. Unit is required.
- Soft-deleted products never appear in any list.

Done when owner A cannot read or edit owner B's data, and tests cover filters,
distance ordering, soft delete, image validation and availability sync.

## Stage 2: Addresses and cart

Addresses (customers only):

- `GET, POST /api/v1/addresses/`; `GET, PATCH, DELETE /api/v1/addresses/{id}/`;
  `POST /api/v1/addresses/{id}/set-default/` (atomic).
- The first address becomes the default automatically. If the default is deleted, the
  most recently added remaining address becomes the default.

Cart (customers only):

- `GET /api/v1/cart/`; `DELETE /api/v1/cart/` (clear)
- `POST /api/v1/cart/items/` `{product_id, quantity}`
- `PATCH /api/v1/cart/items/{id}/` `{quantity}`; `DELETE /api/v1/cart/items/{id}/`

Rules:

- One cart holds one store's products. Adding from another store returns 409
  CART_STORE_CONFLICT unless `?replace=true`, which empties the cart first. An empty
  cart has `store = NULL`.
- Validation: product not deleted and AVAILABLE, store active and OPEN,
  1 <= quantity <= stock. Codes: PRODUCT_UNAVAILABLE (hidden, deleted or inactive
  category), STORE_CLOSED, INSUFFICIENT_STOCK (including sold out, `max_available: 0`).
- Totals count only lines the customer can buy now (`counted_in_total`). The delivery
  fee is 0 when no line counts.
- Adding a product already in the cart increases its quantity.
- GET returns the store summary, items (name, image, unit, current price, quantity,
  line_total, price_changed, available, max_available), subtotal, delivery_fee, total
  and warnings. Totals use current product prices.
- Stock is not reserved by the cart.

Done when tests cover the conflict flow, stock limits, the price change flag, and that
customers cannot see each other's carts or addresses.

## Stage 3: Orders and state machine

`orders/state_machine.py` holds a declarative transition table:

| From | To | Actor |
|---|---|---|
| PENDING | ACCEPTED | store owner |
| PENDING | REJECTED (reason required) | store owner |
| PENDING | CANCELLED | customer |
| ACCEPTED | PREPARING | store owner |
| ACCEPTED | CANCELLED (reason required) | store owner, admin |
| PREPARING | READY | store owner |
| PREPARING | CANCELLED (reason required) | store owner, admin |
| READY | COMPLETED | store owner |

REJECTED, CANCELLED and COMPLETED are terminal. ASSIGNED and OUT_FOR_DELIVERY exist
in the enum but are disabled. Admin may cancel any non-terminal order.

`orders/services.py`:

- `create_order(customer, address_id, payment_method, payer_phone, notes)` in one
  atomic block:
  1. lock the cart and items; reject an empty cart (EMPTY_CART);
  2. check the store is active and OPEN and the address belongs to the customer;
  3. lock products with `select_for_update`, ordered by id;
  4. validate stock, availability and non-deleted status;
  5. recompute unit prices, subtotal and total from the database; delivery fee comes
     from `store.delivery_fee`;
  6. create the Order with snapshots and a unique `BDM-YYYYMMDD-NNNN` number (safe
     under concurrency) and OrderItems with snapshots;
  7. decrement stock with `F()` and update availability;
  8. write OrderStatusHistory (NULL to PENDING);
  9. create a PENDING Payment row;
  10. clear the cart.
- `transition_order(order, action, actor, reason=None)`: validate against the state
  machine, lock the order, write history, restore stock on REJECTED/CANCELLED.
- `orders/events.py`: stub `notify_order_event(order, event)` called via
  `transaction.on_commit`.

Customer endpoints:

- `POST /api/v1/orders/` `{address_id, payment_method, payer_phone?, notes?}`
- `GET /api/v1/orders/` (own; filter by status; newest first)
- `GET /api/v1/orders/{id}/` (items, status history, payment status)
- `POST /api/v1/orders/{id}/cancel/` `{reason?}` (PENDING only)

Admin endpoint (added by decision on 2026-10-08):

- `POST /api/v1/admin/orders/{id}/cancel/` `{reason}` cancels any non-terminal order.

Done when every legal transition passes and every illegal one is rejected; a threaded
concurrency test proves two customers cannot both buy the last unit; price tampering
has no effect; stock is restored exactly once; customers cannot read others' orders.

## Stage 4: Store order management and dashboard

- `GET /api/v1/owner/stores/{id}/orders/` (filters: status, date range, search by
  order number or customer name)
- `GET /api/v1/owner/orders/{id}/`
- `POST /api/v1/owner/orders/{id}/transition/`
  `{action: accept|reject|prepare|ready|complete|cancel, reason?}`
- `GET /api/v1/owner/stores/{id}/dashboard/`: total_orders, pending_orders,
  total_sales (COMPLETED only), low_stock_items, last 7 days of daily sales,
  recent_orders.
- `GET /api/v1/owner/stores/{id}/analytics/?from=&to=`: totals, completed, pending,
  daily sales series, top products by quantity sold.

Rules: database aggregation only (Sum, Count, TruncDate in local time); validate the
date range; reason is mandatory for reject and cancel.

As built: sales are the `total_amount` of COMPLETED orders, bucketed by the local day
the order was placed. Daily series include zero days. Analytics defaults to the last
30 days and allows at most 366. Top products count COMPLETED orders only.

## Stage 5: Payments

- `payments/providers/base.py`: abstract PaymentProvider (initiate, verify_webhook,
  parse_event); CashProvider, MockMobileMoneyProvider and a RealGatewayProvider
  skeleton with TODOs only. Provider chosen by payment_method; secrets from env vars.
- `POST /api/v1/orders/{id}/pay/` (initiate or retry FAILED; rate-limited)
- `GET /api/v1/orders/{id}/payment/`
- `POST /api/v1/payments/webhook/{provider}/` (no login, signature-verified)

Rules: SUCCESS only from a verified webhook; idempotent webhook handling; paid amount
must equal the order total; non-cash orders are hidden from the owner until paid; cash
becomes SUCCESS when the order is COMPLETED; `expire_unpaid_orders` command
(`PAYMENT_TIMEOUT_MINUTES`, default 15); REFUND_REQUIRED note when a paid order is
cancelled.

## Stage 6: Notifications (in-app only)

- `notifications/services.py`: `create_notification(user, type, title, message,
  order=None)`, always via `transaction.on_commit`.
- Events: ORDER_RECEIVED (customer; store owner immediately for cash, after payment
  for non-cash), every status change to the customer, customer cancel to the owner,
  PAYMENT_SUCCESS/PAYMENT_FAILED to the customer, LOW_STOCK to the owner once per
  crossing.
- `GET /api/v1/notifications/` (filter is_read),
  `GET /api/v1/notifications/unread-count/`,
  `POST /api/v1/notifications/{id}/read/`, `POST /api/v1/notifications/read-all/`.

## Decisions log

- **2026-10-08, availability:** UNAVAILABLE always stays UNAVAILABLE until the owner
  changes it.
- **2026-10-08, cart totals:** only buyable lines count toward the subtotal.
- **2026-10-08, store logo:** keep the API field and column name `logo`.
- **2026-10-08, refunds:** paying is only possible for what the store has, so refunds
  are expected mainly for overpayment or double payment. Stage 5 records a
  REFUND_REQUIRED order-history note for a wrong amount, a second payment, a payment
  arriving after cancel or reject, and cancelling or rejecting a paid order. Refunds
  themselves are manual.
- **2026-10-08, admin cancel:** built as an API endpoint for a future admin screen.
- **2026-10-08, sales:** counted on the order day and include the delivery fee.
- **2026-10-08, payment expiry:** only unpaid mobile money orders expire. Cash orders
  never do. An order with a prompt still PROCESSING also expires; if its money arrives
  later, the webhook records it and adds a REFUND_REQUIRED note.
- **2026-10-08, notifications:** the customer is told about every status change,
  including their own cancel. A cancel not made by the store owner (customer, admin,
  expiry) also tells the store owner, but only if the store could already see the
  order. LOW_STOCK is raised by customer orders only, not by the owner editing stock.

## Follow-ups after all stages

- **Remind the developer:** they have questions about the admin cancel endpoint and
  admin screens. Raise this once Stages 0-7 are done.

## Stage 7: Frontend handoff

- Generate `docs/openapi.yaml` (validated).
- End-to-end order flow test.
- `docs/FRONTEND_HANDOFF.md`: auth, conventions, every error code, enums,
  transitions, a screen-to-endpoint map with real JSON, unsupported mockup features,
  a must/must-not checklist, demo logins via environment variable names only, and
  TypeScript type generation.
