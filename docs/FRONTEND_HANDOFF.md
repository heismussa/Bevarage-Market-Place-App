# Frontend handoff

Everything the frontend needs to build against the backend. It describes the code as
it is today. The JSON examples are real responses captured from the seeded demo data
(tokens and passwords removed); the two marked "illustrative" have the real shape with
made-up values.

- Machine-readable contract: [`docs/openapi.yaml`](openapi.yaml) (generate types from it, see section 7).
- Interactive docs while the stack runs: <http://localhost:8000/api/docs/>.
- Business rules and decisions: [`docs/BACKEND_PLAN.md`](BACKEND_PLAN.md).

Contents:

1. [Base URL, auth and roles](#1-base-url-auth-and-roles)
2. [Conventions](#2-conventions)
3. [Enums and the order state machine](#3-enums-and-the-order-state-machine)
4. [Screens and their endpoints](#4-screens-and-their-endpoints)
5. [Features the backend does not support](#5-features-the-backend-does-not-support)
6. [Frontend must / must not](#6-frontend-must--must-not)
7. [Demo logins and TypeScript types](#7-demo-logins-and-typescript-types)

---

## 1. Base URL, auth and roles

### Base URL

| Environment | Base URL |
| --- | --- |
| Local Docker | `http://localhost:8000/api/v1/` |

Every path in this document is relative to the base URL. The browser origin of the
frontend must be listed in `CORS_ALLOWED_ORIGINS` in the backend `.env`
(the example file allows `http://localhost:3000`).

### Login flow (JWT)

Users log in with **phone + password**. There are no sessions or cookies.

1. `POST auth/login/` with `{"phone": "+255712345002", "password": "..."}` returns
   `{"refresh": "<jwt>", "access": "<jwt>"}`.
2. Send the access token on every protected call:
   `Authorization: Bearer <access>`.
3. The access token lives **30 minutes** (`JWT_ACCESS_MINUTES`), the refresh token
   **7 days** (`JWT_REFRESH_DAYS`).
4. When a call returns `401` with code `TOKEN_INVALID`, call `POST auth/refresh/` with
   `{"refresh": "<jwt>"}`. It returns only a new `{"access": "<jwt>"}`; keep the same
   refresh token. Retry the original call once.
5. If the refresh call also returns `401 TOKEN_INVALID`, the session is over: clear the
   tokens and go to the login screen.
6. Logout is client-side only: delete both tokens. There is no logout endpoint.

After login, call `GET auth/me/` to learn the user's `role` and route to the customer
or store-owner app.

```json
{
  "id": 2,
  "full_name": "John Mushi",
  "phone": "+255712345002",
  "email": "customer@example.com",
  "role": "CUSTOMER",
  "is_staff": false,
  "is_active": true,
  "created_at": "2026-10-07T21:12:22.467881+03:00",
  "updated_at": "2026-10-07T21:12:22.467892+03:00"
}
```

Registration: `POST auth/register/` with `full_name`, `phone`, `password`, optional
`email`, and `role` (`CUSTOMER` or `STORE_OWNER` only). It returns the user (201) but
**no tokens**: call login right after.

```json
{"id": 5, "full_name": "Asha Mollel", "phone": "+255754000222", "email": "asha@example.com", "role": "CUSTOMER"}
```

### Roles and what each may call

Anything not listed for a role is refused. A wrong role gets `403 PERMISSION_DENIED`;
an object that belongs to someone else gets `404 NOT_FOUND` (never 403), so the app
cannot tell whether it exists.

| Area | Endpoints | Anonymous | Customer | Store owner | Admin |
| --- | --- | :-: | :-: | :-: | :-: |
| Health | `health/` | yes | yes | yes | yes |
| Auth | `auth/register/`, `auth/login/`, `auth/refresh/` | yes | yes | yes | yes |
| Profile | `auth/me/` (GET, PATCH) | | yes | yes | yes |
| Catalog (read only) | `categories/`, `stores/`, `stores/{id}/`, `stores/{store_id}/products/`, `products/{id}/` | yes | yes | yes | yes |
| Addresses | `addresses/`, `addresses/{id}/`, `addresses/{id}/set-default/` | | yes | | |
| Cart | `cart/`, `cart/items/`, `cart/items/{id}/` | | yes | | |
| Orders | `orders/`, `orders/{id}/`, `orders/{id}/cancel/` | | yes | | |
| Payments | `orders/{id}/pay/`, `orders/{id}/payment/` | | yes | | |
| My stores | `owner/stores/`, `owner/stores/{id}/` | | | yes | |
| My products | `owner/stores/{store_id}/products/`, `owner/products/{id}/`, `owner/products/{id}/stock/` | | | yes | |
| Store orders | `owner/stores/{id}/orders/`, `owner/orders/{id}/`, `owner/orders/{id}/transition/` | | | yes | |
| Reports | `owner/stores/{id}/dashboard/`, `owner/stores/{id}/analytics/` | | | yes | |
| Notifications | `notifications/`, `notifications/unread-count/`, `notifications/{id}/read/`, `notifications/read-all/` | | yes | yes | yes |
| Admin | `admin/orders/{id}/cancel/` | | | | yes |
| Webhooks | `payments/webhook/{provider}/` | payment provider only, never the app | | | |

---

## 2. Conventions

### Pagination

Every list endpoint is paginated: `?page=2&page_size=50`. Default 20, maximum 100.

```json
{
  "count": 6,
  "next": "http://localhost:8000/api/v1/stores/1/products/?page=2&page_size=2",
  "previous": null,
  "results": []
}
```

`next` and `previous` are full URLs (or `null`); follow them as they are.

### Errors

Every error has the same body:

```json
{"error": {"code": "INSUFFICIENT_STOCK", "message": "Only 45 of Red Bull 250ml left in stock.", "details": {"product_id": 5, "requested": 999, "max_available": 45}}}
```

- Switch on `error.code`, never on `message` (messages may change wording).
- `message` is a readable English sentence that is safe to show to the user.
- `details` is always an object, sometimes empty.
- For `VALIDATION_ERROR`, `details` maps field names to lists of messages; show each
  under its form field. `message` is the first of them.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Enter a phone number in +255 format followed by 9 digits (for example +255712345678).",
    "details": {
      "phone": ["Enter a phone number in +255 format followed by 9 digits (for example +255712345678)."],
      "role": ["\"ADMIN\" is not a valid choice."]
    }
  }
}
```

#### Every error code

| HTTP | Code | When it happens | Suggested UI |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | A field is missing or invalid (also wrong query parameters, e.g. `ordering=distance` without `lat`/`lng`, or a reject without `reason`). | Show `details[field]` under each field; show `message` in a toast if no field matches. |
| 400 | `PARSE_ERROR` | The body is not valid JSON. | Treat as a bug; generic "Something went wrong". |
| 401 | `NOT_AUTHENTICATED` | No `Authorization` header on a protected call. | Go to login. |
| 401 | `AUTHENTICATION_FAILED` | Wrong phone or password at login. | "Wrong phone number or password." Do not try a refresh. |
| 401 | `TOKEN_INVALID` | Access or refresh token expired, malformed or revoked. | Refresh once and retry; if refresh fails, log out. |
| 401 | `INVALID_SIGNATURE` | Payment webhook signature is wrong. Server-to-server only. | Never seen by the app. |
| 403 | `PERMISSION_DENIED` | The user's role may not call this endpoint (e.g. a store owner opening the cart). | Route the user to their own app; this is a navigation bug. |
| 404 | `NOT_FOUND` | The object does not exist **or belongs to someone else**; also unknown URLs. | "Not found" screen, or refresh the list it came from. |
| 405 | `METHOD_NOT_ALLOWED` | Wrong HTTP method. | Bug. |
| 406 | `NOT_ACCEPTABLE` | Unsupported `Accept` header. | Bug; send `Accept: application/json` or nothing. |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Wrong `Content-Type`. | Bug; JSON bodies use `application/json`, uploads `multipart/form-data`. |
| 429 | `THROTTLED` | Too many requests. Today only `orders/{id}/pay/` (5 per minute per customer). | "Please wait `details.wait_seconds` seconds"; disable the button for that long. |
| 409 | `CONFLICT` | Generic conflict with the current state (fallback). | Reload the screen's data and show `message`. |
| 409 | `CART_STORE_CONFLICT` | Adding a product from a different store than the one in the cart. `details`: `cart_store_id`, `cart_store_name`, `product_store_id`, `product_store_name`. | Dialog: "Your cart has items from {cart_store_name}. Start a new cart?" On yes, repeat the call with `?replace=true`. |
| 409 | `PRODUCT_UNAVAILABLE` | Product deleted, its category hidden, or the owner marked it UNAVAILABLE. Cart: `details` has `product_id`, `store_id`. Checkout: see `details.problems`. | Show `message`; remove or grey out the item. |
| 409 | `STORE_CLOSED` | The store is CLOSED or deactivated. | "This store is not taking orders right now." Disable add-to-cart and checkout. |
| 409 | `INSUFFICIENT_STOCK` | Quantity is more than stock (also when sold out: `max_available` 0). `details`: `product_id`, `requested`, `max_available`. | Offer to set the quantity to `max_available`, or remove the line if it is 0. |
| 409 | `EMPTY_CART` | Checkout with an empty cart (also a double-tapped "Place order"). | Go to the order list; the first tap probably succeeded. |
| 409 | `INVALID_TRANSITION` | The order is no longer in a state that allows the action (e.g. customer cancels after the store accepted). `details`: `order_status`, `action`, `allowed_actions`. | Reload the order and show `message`; only render buttons from `allowed_actions`. |
| 409 | `PAYMENT_NOT_ALLOWED` | Pay on a cash order, an order already paid, or an order no longer PENDING. | Reload the order; hide the Pay button. |
| 409 | `PAYMENT_IN_PROGRESS` | A mobile-money prompt is already waiting. `details.payment_id`. | Keep showing "Check your phone" and keep polling the payment. |
| 500 | `INTERNAL_ERROR` | Unexpected server error. The message never contains internal details. | Generic "Something went wrong, try again". |

Checkout (`POST orders/`) reports **every** blocking cart line at once in
`details.problems`; `code` and `message` describe the first one (illustrative example
in the real shape):

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Only 2 of Sprite 500ml left in stock.",
    "details": {
      "problems": [
        {"code": "INSUFFICIENT_STOCK", "product_id": 3, "name": "Sprite 500ml", "requested": 4, "max_available": 2},
        {"code": "PRODUCT_UNAVAILABLE", "product_id": 6, "name": "Kilimanjaro Premium Lager"}
      ]
    }
  }
}
```

### Data formats

| Kind | Format | Example |
| --- | --- | --- |
| Money | String with exactly 2 decimals, Tanzanian shillings. Send strings too. | `"1500.00"` |
| Coordinates | String with 6 decimals | `"-6.823490"` |
| `distance_km` | Number (km, 2 decimals) or `null` | `8.09` |
| Date-time | ISO 8601 with the local offset `+03:00` | `"2026-10-08T14:50:49.451692+03:00"` |
| Date | `YYYY-MM-DD` | `"2026-10-08"` |
| IDs | Integers | `12` |
| Phone | `+255` followed by 9 digits | `"+255712345678"` |
| Images | Absolute URL, or `null` when none | `null` |

- **Time zone.** The server runs in `Africa/Dar_es_Salaam` (UTC+3, no daylight saving).
  Day-based filters and reports (`date_from`, `date_to`, `from`, `to`, daily sales)
  use local calendar days and include both ends.
- **Never do money maths for anything that is sent back.** Parse money strings with a
  decimal library (or as integers of cents) only for display. Totals always come from
  the server.

### Image uploads

- Store `logo` and product `image` are uploaded with `multipart/form-data` on the same
  create/update endpoints (`owner/stores/`, `owner/stores/{id}/`,
  `owner/stores/{store_id}/products/`, `owner/products/{id}/`). Without a file, send JSON.
- Only real **JPEG, PNG or WebP**, at most **2 MB**. The content is checked, not the
  file name. Otherwise `400 VALIDATION_ERROR` on the field
  (`"Image must be 2 MB or smaller."` or `"Upload a valid JPEG, PNG or WebP image."`).
- Resize and compress on the device before uploading.

### Filtering, search and ordering

- `?search=` matches the listed text fields (case-insensitive, partial).
- `?ordering=field` ascending, `?ordering=-field` descending.

| Endpoint | Filters | `search` fields | `ordering` fields (default) |
| --- | --- | --- | --- |
| `categories/` | | `name` | `name` (`name`) |
| `stores/` | `status`, `city`, `area` (exact, any case), `category` (id), `lat` + `lng` | `store_name`, `description`, `location`, `city`, `area` | `store_name`, `delivery_fee`, `created_at`, `distance` (`store_name`) |
| `stores/{id}/` | `lat` + `lng` (adds `distance_km`) | | |
| `stores/{store_id}/products/` | `category` (id), `availability`, `in_stock` (true/false) | `name`, `description` | `name`, `price` (`name`) |
| `addresses/` | `is_default`, `city` | `address_name`, `address_line`, `area` | `address_name`, `created_at` (default first) |
| `orders/` | `status` | `order_number`, `store__store_name` | `ordered_at`, `total_amount` (`-ordered_at`) |
| `owner/stores/` | | `store_name`, `city`, `area` | `store_name`, `created_at` (`store_name`) |
| `owner/stores/{store_id}/products/` | `category`, `availability`, `low_stock` (true/false) | `name`, `description` | `name`, `price`, `stock_quantity`, `created_at` (`name`) |
| `owner/stores/{id}/orders/` | `status`, `payment_status`, `date_from`, `date_to` | `order_number`, customer full name | `ordered_at`, `total_amount` (`-ordered_at`) |
| `owner/stores/{id}/analytics/` | `from`, `to` (default last 30 days, max 366 days) | | |
| `notifications/` | `is_read` | | newest first |

`lat` and `lng` must be sent together. `ordering=distance` without them is a
`400 VALIDATION_ERROR`. Stores without coordinates sort last.

---

## 3. Enums and the order state machine

The OpenAPI file names these enums, so generated types match exactly.

| Enum | Values | Notes |
| --- | --- | --- |
| `UserRoleEnum` | `ADMIN`, `CUSTOMER`, `STORE_OWNER`, `DRIVER` | `DRIVER` is reserved; no driver features exist. |
| `RegistrationRoleEnum` | `CUSTOMER`, `STORE_OWNER` | The only roles accepted by register. |
| `StoreStatusEnum` | `OPEN`, `CLOSED` | Set by the owner. New stores start `CLOSED`. |
| Category status | `ACTIVE`, `INACTIVE` | Only active categories are ever returned. |
| Product `unit` | `BOTTLE`, `CAN`, `CRATE`, `CARTON`, `PACK` | |
| `availability_status` | `AVAILABLE`, `OUT_OF_STOCK`, `UNAVAILABLE` | `OUT_OF_STOCK` is automatic when stock hits 0 and clears on restock. `UNAVAILABLE` is the owner's switch and stays until the owner changes it. Owners may only send `AVAILABLE` or `UNAVAILABLE`. |
| `OrderStatusEnum` | `PENDING`, `ACCEPTED`, `REJECTED`, `PREPARING`, `READY`, `ASSIGNED`, `OUT_FOR_DELIVERY`, `COMPLETED`, `CANCELLED` | `ASSIGNED` and `OUT_FOR_DELIVERY` are reserved for drivers and never happen today. |
| `PaymentStatusEnum` | `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`, `CANCELLED`, `REFUNDED` | `REFUNDED` is never set today (refunds are manual). |
| `PaymentMethodEnum` | `MPESA`, `TIGO_PESA`, `AIRTEL_MONEY`, `CARD`, `BANK`, `CASH` | Appears on existing payments. |
| `CheckoutPaymentMethodEnum` | `CASH`, `MPESA`, `TIGO_PESA`, `AIRTEL_MONEY` | What checkout accepts. `CARD` and `BANK` are not accepted. |
| `OrderActionEnum` | `accept`, `reject`, `prepare`, `ready`, `complete`, `cancel` | Lowercase. |
| Notification type | `ORDER_RECEIVED`, `ORDER_ACCEPTED`, `ORDER_REJECTED`, `ORDER_PREPARING`, `ORDER_READY`, `ORDER_COMPLETED`, `ORDER_CANCELLED`, `PAYMENT_SUCCESS`, `PAYMENT_FAILED`, `LOW_STOCK`, `DRIVER_ASSIGNED`, `OUT_FOR_DELIVERY` | The last two are never sent today. |
| Cart warning code | `STORE_CLOSED`, `PRODUCT_UNAVAILABLE`, `INSUFFICIENT_STOCK`, `PRICE_CHANGED` | In `cart.warnings`, not errors. |

### Order status transitions

`PENDING → ACCEPTED → PREPARING → READY → COMPLETED`, with exits to `REJECTED` or
`CANCELLED`. `REJECTED`, `CANCELLED` and `COMPLETED` are final.

| From | Action | Who | To | Reason |
| --- | --- | --- | --- | --- |
| PENDING | `accept` | Store owner | ACCEPTED | |
| PENDING | `reject` | Store owner | REJECTED | required |
| PENDING | `cancel` | Customer | CANCELLED | optional |
| PENDING | `cancel` | Admin | CANCELLED | required |
| PENDING | `cancel` | System (unpaid mobile money after 15 minutes) | CANCELLED | automatic |
| ACCEPTED | `prepare` | Store owner | PREPARING | |
| ACCEPTED | `cancel` | Store owner or Admin | CANCELLED | required |
| PREPARING | `ready` | Store owner | READY | |
| PREPARING | `cancel` | Store owner or Admin | CANCELLED | required |
| READY | `complete` | Store owner | COMPLETED | |
| READY | `cancel` | Admin | CANCELLED | required |

Customers can cancel **only while PENDING**. The reason, when given, is stored in
`status_reason` and shown in the order's `status_history[].notes`.

What each transition does besides changing the status:

| Result | Stock | Payment | Notifications |
| --- | --- | --- | --- |
| Order placed (PENDING) | Taken from each product at checkout. Not reserved before that. | A PENDING payment row is created. | Customer: `ORDER_RECEIVED`. Store owner: `ORDER_RECEIVED` now for cash, after payment SUCCESS for mobile money. Store owner: `LOW_STOCK` for each product that just dropped to or below its threshold. |
| ACCEPTED, PREPARING, READY | No change | No change | Customer: `ORDER_ACCEPTED` / `ORDER_PREPARING` / `ORDER_READY`. |
| COMPLETED | No change | A cash payment becomes SUCCESS. | Customer: `ORDER_COMPLETED`. |
| REJECTED | Returned to stock | Unstarted payments become CANCELLED. If already paid, a `REFUND_REQUIRED` note is added (refund is manual). | Customer: `ORDER_REJECTED` with the reason. |
| CANCELLED | Returned to stock | As for REJECTED. | Customer: `ORDER_CANCELLED`. The store owner too, when someone other than the owner cancelled and the store could already see the order. |

Payment events: a successful mobile-money payment notifies the customer
(`PAYMENT_SUCCESS`) and the store owner (`ORDER_RECEIVED`); a failed one notifies only
the customer (`PAYMENT_FAILED`).

**Never hard-code which buttons to show.** Order detail responses include
`allowed_actions` for the current user; render exactly those.

---

## 4. Screens and their endpoints

### Customer app

#### Splash and auth

| Step | Call |
| --- | --- |
| App start with saved tokens | `GET auth/me/` (refresh on `TOKEN_INVALID`); route by `role` |
| Sign up | `POST auth/register/`, then `POST auth/login/` |
| Log in | `POST auth/login/` |

Example of a wrong password at login (`401`):

```json
{"error": {"code": "AUTHENTICATION_FAILED", "message": "No active account found with the given credentials", "details": {}}}
```

#### Home (stores near me, categories)

| Need | Call |
| --- | --- |
| Category chips | `GET categories/` |
| Nearby stores | `GET stores/?lat=-6.7924&lng=39.2083&ordering=distance` |
| Stores selling a category | `GET stores/?category=1` |
| Search | `GET stores/?search=kariakoo` |

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "store_name": "ABC Drinks",
      "description": "Soft drinks, water, and beer from Kariakoo.",
      "logo": null,
      "location": "Kariakoo Market, Uhuru Street, Dar es Salaam",
      "city": "Dar es Salaam",
      "area": "Kariakoo",
      "latitude": "-6.823490",
      "longitude": "39.274530",
      "phone": "+255713000001",
      "email": "abc@example.com",
      "status": "OPEN",
      "delivery_fee": "2000.00",
      "distance_km": 8.09
    },
    {
      "id": 2,
      "store_name": "Fresh Beverages",
      "description": "Juices, water, and wine from Masaki.",
      "logo": null,
      "location": "Masaki Peninsula, Toure Drive, Dar es Salaam",
      "city": "Dar es Salaam",
      "area": "Masaki",
      "latitude": "-6.747800",
      "longitude": "39.279200",
      "phone": "+255713000002",
      "email": "fresh@example.com",
      "status": "OPEN",
      "delivery_fee": "2500.00",
      "distance_km": 9.27
    }
  ]
}
```

`GET categories/` returns `{"id": 1, "name": "Soda", "slug": "soda", "description": "Soda"}` items.
Closed stores are listed (with `status: "CLOSED"`) so the app can show them greyed out;
filter with `?status=OPEN` to hide them.

#### Store page

| Need | Call |
| --- | --- |
| Store header | `GET stores/{id}/` (add `lat`/`lng` for `distance_km`) |
| Products | `GET stores/{id}/products/` with `category`, `in_stock`, `search`, `ordering=price` |

```json
{
  "id": 1,
  "store": 1,
  "store_name": "ABC Drinks",
  "category": {"id": 1, "name": "Soda", "slug": "soda"},
  "name": "Coca-Cola 500ml",
  "description": "Coca-Cola 500ml",
  "image": null,
  "unit": "BOTTLE",
  "price": "1500.00",
  "stock_quantity": 120,
  "availability_status": "AVAILABLE",
  "in_stock": true
}
```

#### Product detail

`GET products/{id}/` returns the same shape as one item above. Disable "Add to cart"
when `in_stock` is false, `availability_status` is not `AVAILABLE`, or the store is `CLOSED`.

#### Cart

| Need | Call |
| --- | --- |
| Show cart | `GET cart/` |
| Add | `POST cart/items/` `{"product_id": 1, "quantity": 2}` (adds to an existing line) |
| Add from another store | `POST cart/items/?replace=true` after the user agrees |
| Change quantity | `PATCH cart/items/{line id}/` `{"quantity": 3}` |
| Remove line | `DELETE cart/items/{line id}/` |
| Empty cart | `DELETE cart/` |

Every cart call returns the whole cart, so replace your cart state with the response.
Here the owner raised the Coca-Cola price after it was added:

```json
{
  "store": {"id": 1, "store_name": "ABC Drinks", "logo": null, "status": "OPEN", "delivery_fee": "2000.00"},
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "name": "Coca-Cola 500ml",
      "image": null,
      "unit": "BOTTLE",
      "unit_price": "1600.00",
      "price_when_added": "1500.00",
      "quantity": 2,
      "line_total": "3200.00",
      "price_changed": true,
      "available": true,
      "max_available": 120,
      "counted_in_total": true
    },
    {
      "id": 2,
      "product_id": 3,
      "name": "Sprite 500ml",
      "image": null,
      "unit": "CAN",
      "unit_price": "1500.00",
      "price_when_added": "1500.00",
      "quantity": 2,
      "line_total": "3000.00",
      "price_changed": false,
      "available": true,
      "max_available": 6,
      "counted_in_total": true
    }
  ],
  "item_count": 4,
  "subtotal": "6200.00",
  "delivery_fee": "2000.00",
  "total": "8200.00",
  "warnings": [
    {"code": "PRICE_CHANGED", "message": "The price of Coca-Cola 500ml changed from 1500.00 to 1600.00.", "item_id": 1}
  ]
}
```

- Totals use current prices and count only lines with `counted_in_total: true`.
- Show every `warnings[]` entry next to its line (`item_id`) or at the top (`item_id: null`).
- Stock is not reserved by the cart; it is checked again at checkout.
- An empty cart is `{"store": null, "items": [], "item_count": 0, "subtotal": "0.00", "delivery_fee": "0.00", "total": "0.00", "warnings": []}`.

Adding from a second store (`409`):

```json
{"error": {"code": "CART_STORE_CONFLICT", "message": "Your cart has items from another store. Clear it to add this product.", "details": {"cart_store_id": 1, "cart_store_name": "ABC Drinks", "product_store_id": 2, "product_store_name": "Fresh Beverages"}}}
```

#### Checkout

| Need | Call |
| --- | --- |
| Pick address | `GET addresses/` (default first) |
| Place order | `POST orders/` |

```json
{"address_id": 1, "payment_method": "CASH", "notes": "Please call on arrival."}
```

For mobile money send `"payment_method": "MPESA"` (or `TIGO_PESA`, `AIRTEL_MONEY`) and
optionally `"payer_phone"` (defaults to the account phone). Only these four fields are
read; any price or total in the body is ignored. Response (`201`), the order detail:

```json
{
  "id": 1,
  "order_number": "BDM-20261008-0001",
  "store": {"id": 1, "store_name": "ABC Drinks", "logo": null, "phone": "+255713000001"},
  "order_status": "PENDING",
  "payment_status": "PENDING",
  "status_reason": null,
  "delivery_address": "Plot 12, Haile Selassie Road, Msasani, Dar es Salaam",
  "delivery_phone": "+255712345002",
  "delivery_latitude": "-6.748900",
  "delivery_longitude": "39.276800",
  "subtotal_amount": "6000.00",
  "delivery_fee": "2000.00",
  "total_amount": "8000.00",
  "notes": "Please call on arrival.",
  "items": [
    {"id": 1, "product": 1, "product_name": "Coca-Cola 500ml", "unit": "BOTTLE", "quantity": 2, "unit_price": "1500.00", "subtotal": "3000.00"},
    {"id": 2, "product": 3, "product_name": "Sprite 500ml", "unit": "CAN", "quantity": 2, "unit_price": "1500.00", "subtotal": "3000.00"}
  ],
  "status_history": [
    {"from_status": null, "status": "PENDING", "changed_at": "2026-10-08T14:50:49.482911+03:00", "changed_by_role": "CUSTOMER", "notes": null}
  ],
  "payment": {"id": 1, "payment_method": "CASH", "payment_status": "PENDING", "amount": "8000.00", "currency": "TZS", "payer_phone": null},
  "allowed_actions": ["cancel"],
  "ordered_at": "2026-10-08T14:50:49.451692+03:00",
  "updated_at": "2026-10-08T14:50:49.451729+03:00"
}
```

The cart is emptied on success. Item names, prices and the delivery address are
snapshots: they do not change if the product or address is edited later.

**Mobile money payment** (after placing an MPESA, TIGO_PESA or AIRTEL_MONEY order):

1. `POST orders/{id}/pay/` with `{}` or `{"payer_phone": "+255712345002"}`:

   ```json
   {
     "payment": {
       "id": 2,
       "payment_method": "MPESA",
       "payment_status": "PROCESSING",
       "amount": "5000.00",
       "currency": "TZS",
       "payer_phone": "+255712345002",
       "transaction_reference": "MOCK-A61ADBB0141E4825A6FC",
       "payment_time": null,
       "created_at": "2026-10-08T14:50:50.023732+03:00"
     },
     "instructions": "A payment prompt for 5000.00 TZS was sent to +255712345002. Enter your PIN to approve."
   }
   ```

2. Show `instructions`, then poll `GET orders/{id}/payment/` every 3 seconds until
   `payment_status` is `SUCCESS` or `FAILED` (stop polling after about 2 minutes and
   offer a "Check again" button).
3. `SUCCESS`: go to order tracking. The response then has a `payment_time`.
4. `FAILED`: offer "Try again", which calls `POST orders/{id}/pay/` again (a new attempt).
5. An unpaid mobile-money order is cancelled automatically after
   `PAYMENT_TIMEOUT_MINUTES` (15 by default); the customer gets `ORDER_CANCELLED`.

`pay/` never marks a payment as paid; only the provider's confirmation does. While a
prompt is waiting, another `pay/` returns `409 PAYMENT_IN_PROGRESS`; after success,
`409 PAYMENT_NOT_ALLOWED` (`"This order is already paid."`).

**Cash**: nothing to do at checkout. `payment_status` stays `PENDING` until the store
completes the order, then becomes `SUCCESS`.

#### Order tracking

`GET orders/{id}/`: same shape as the checkout response. Poll every 15 to 30 seconds
while the screen is open and the order is not final. Use:

- `order_status` for the progress bar (PENDING, ACCEPTED, PREPARING, READY, COMPLETED);
- `status_history` for the timeline (`changed_by_role: null` means the system);
- `status_reason` for why it was rejected or cancelled;
- `allowed_actions` for the Cancel button.

Cancel: `POST orders/{id}/cancel/` with optional `{"reason": "Ordered by mistake"}`.
Too late (`409`):

```json
{"error": {"code": "INVALID_TRANSITION", "message": "You cannot cancel an order that is ACCEPTED.", "details": {"order_status": "ACCEPTED", "action": "cancel", "allowed_actions": []}}}
```

#### Order history

`GET orders/` (filter `?status=COMPLETED`, search by order number or store name):

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 2,
      "order_number": "BDM-20261008-0002",
      "store": {"id": 1, "store_name": "ABC Drinks", "logo": null, "phone": "+255713000001"},
      "order_status": "PENDING",
      "payment_status": "SUCCESS",
      "total_amount": "5000.00",
      "item_count": 1,
      "ordered_at": "2026-10-08T14:50:50.008237+03:00"
    }
  ]
}
```

`item_count` is the number of different products, not the number of bottles.

#### Profile and addresses

| Need | Call |
| --- | --- |
| Profile | `GET auth/me/`, `PATCH auth/me/` (`full_name`, `phone`, `email`; `role` cannot change) |
| Addresses | `GET addresses/`, `POST addresses/`, `GET/PATCH/DELETE addresses/{id}/` |
| Make default | `POST addresses/{id}/set-default/` |

```json
{
  "id": 2,
  "address_name": "Office",
  "address_line": "Plot 7, Ali Hassan Mwinyi Road",
  "city": "Dar es Salaam",
  "area": "Upanga",
  "latitude": "-6.810900",
  "longitude": "39.287300",
  "phone": "+255712345002",
  "is_default": false,
  "created_at": "2026-10-08T14:50:49.152349+03:00",
  "updated_at": "2026-10-08T14:50:49.152360+03:00"
}
```

- The first address becomes the default automatically. `is_default` cannot be sent;
  use `set-default/`.
- Deleting the default makes the newest remaining address the default.
- `latitude` and `longitude` are optional but must be sent together.

#### Notifications (customer and store owner)

| Need | Call |
| --- | --- |
| Bell badge | `GET notifications/unread-count/` → `{"unread_count": 4}` (poll every 30 to 60 s) |
| List | `GET notifications/` (`?is_read=false` for unread only) |
| Open one | `POST notifications/{id}/read/` (safe to repeat) |
| Mark all read | `POST notifications/read-all/` → `{"updated": 3}` |

```json
{
  "id": 6,
  "notification_type": "PAYMENT_SUCCESS",
  "title": "Payment received",
  "message": "We received 5000.00 TZS for order BDM-20261008-0002.",
  "is_read": false,
  "order": 2,
  "order_number": "BDM-20261008-0002",
  "created_at": "2026-10-08T14:50:50.143004+03:00"
}
```

Tapping a notification with an `order` id opens that order (`orders/{id}/` for
customers, `owner/orders/{id}/` for store owners). `LOW_STOCK` has `order: null`;
open the low-stock view.

### Store-owner app

An owner can have several stores. Load `GET owner/stores/` after login; if there is
one store, select it automatically, otherwise show a store picker. Most owner calls
take the store id.

#### Dashboard

`GET owner/stores/{id}/dashboard/`:

```json
{
  "total_orders": 2,
  "pending_orders": 1,
  "total_sales": "0.00",
  "low_stock_count": 1,
  "low_stock_items": [
    {"id": 3, "name": "Sprite 500ml", "stock_quantity": 4, "low_stock_threshold": 5, "availability_status": "AVAILABLE"}
  ],
  "sales_last_7_days": [
    {"date": "2026-10-02", "orders": 0, "sales": "0.00"},
    {"date": "2026-10-08", "orders": 0, "sales": "0.00"}
  ],
  "recent_orders": [
    {
      "id": 2,
      "order_number": "BDM-20261008-0002",
      "customer": {"full_name": "John Mushi", "phone": "+255712345002"},
      "order_status": "PENDING",
      "payment_status": "SUCCESS",
      "payment_method": "MPESA",
      "total_amount": "5000.00",
      "item_count": 1,
      "ordered_at": "2026-10-08T14:50:50.008237+03:00"
    }
  ]
}
```

(`sales_last_7_days` always has 7 entries, one per day including days with no sales;
shortened here.) Sales count only COMPLETED orders, include the delivery fee, and are
grouped by the day the order was placed. Low-stock items are lowest first, at most 10.

#### Orders list and detail

| Need | Call |
| --- | --- |
| Incoming orders | `GET owner/stores/{id}/orders/?status=PENDING` |
| Filters | `status`, `payment_status`, `date_from`, `date_to`, `search` |
| Detail | `GET owner/orders/{id}/` |
| Act | `POST owner/orders/{id}/transition/` `{"action": "accept"}` |
| Reject or cancel | `{"action": "reject", "reason": "Out of crates"}` (reason required) |

```json
{
  "id": 1,
  "order_number": "BDM-20261008-0001",
  "customer": {"full_name": "John Mushi", "phone": "+255712345002"},
  "order_status": "PENDING",
  "payment_status": "PENDING",
  "payment_method": "CASH",
  "total_amount": "8000.00",
  "item_count": 2,
  "ordered_at": "2026-10-08T14:50:49.451692+03:00"
}
```

The detail is the customer order detail plus `customer`, and `allowed_actions` for
the owner (for a new order: `["accept", "reject"]`). The transition call returns the
updated detail. Mobile-money orders appear here **only after they are paid**; cash
orders appear immediately. Poll the PENDING list every 15 to 30 seconds, or refresh
when an `ORDER_RECEIVED` notification arrives.

Wrong action for the current state (`409`):

```json
{"error": {"code": "INVALID_TRANSITION", "message": "You cannot complete an order that is ACCEPTED.", "details": {"order_status": "ACCEPTED", "action": "complete", "allowed_actions": ["prepare", "cancel"]}}}
```

#### Products: list, add, edit, stock

| Need | Call |
| --- | --- |
| List | `GET owner/stores/{store_id}/products/` |
| Add | `POST owner/stores/{store_id}/products/` |
| Edit | `GET`/`PATCH owner/products/{id}/` |
| Delete | `DELETE owner/products/{id}/` (204; hidden everywhere, past orders keep their snapshot) |
| Quick stock update | `PATCH owner/products/{id}/stock/` `{"stock_quantity": 6}` |
| Hide or show | `PATCH owner/products/{id}/` `{"availability_status": "UNAVAILABLE"}` or `"AVAILABLE"` |

Add request (JSON, or multipart with an `image` file):

```json
{"category": 1, "name": "Pepsi 500ml", "description": "Chilled Pepsi.", "unit": "BOTTLE", "price": "1400.00", "stock_quantity": 48, "low_stock_threshold": 6}
```

Response (`201`); list items have the same shape:

```json
{
  "id": 13,
  "store": 1,
  "category": 1,
  "category_detail": {"id": 1, "name": "Soda", "slug": "soda"},
  "name": "Pepsi 500ml",
  "description": "Chilled Pepsi.",
  "image": null,
  "unit": "BOTTLE",
  "price": "1400.00",
  "stock_quantity": 48,
  "low_stock_threshold": 6,
  "availability_status": "AVAILABLE",
  "is_low_stock": false,
  "created_at": "2026-10-08T14:50:49.694449+03:00",
  "updated_at": "2026-10-08T14:50:49.694475+03:00"
}
```

Rules: price above 0; stock and threshold 0 or more; product names unique per store;
categories come from `GET categories/` (they cannot be created in the app).

#### Low-stock view

`GET owner/stores/{store_id}/products/?low_stock=true` lists products with
`stock_quantity <= low_stock_threshold` (`is_low_stock: true`). The dashboard shows the
top 10, and owners get a `LOW_STOCK` notification each time a customer order pushes a
product to or below its threshold.

#### Sales and analytics

`GET owner/stores/{id}/analytics/?from=2026-10-01&to=2026-10-08` (both optional;
defaults to the last 30 days; at most 366 days):

```json
{
  "date_from": "2026-10-01",
  "date_to": "2026-10-08",
  "total_orders": 2,
  "completed_orders": 0,
  "pending_orders": 1,
  "total_sales": "0.00",
  "daily_sales": [
    {"date": "2026-10-01", "orders": 0, "sales": "0.00"},
    {"date": "2026-10-08", "orders": 0, "sales": "0.00"}
  ],
  "top_products": [
    {"product_id": 1, "product_name": "Coca-Cola 500ml", "quantity_sold": 24, "sales": "36000.00"}
  ]
}
```

(`daily_sales` has one entry per day in the range, shortened here. The `top_products`
entry is illustrative: the capture had no completed orders yet.) Top products are the
10 best by quantity, from COMPLETED orders.

#### Store profile

| Need | Call |
| --- | --- |
| My stores | `GET owner/stores/` |
| Create a store | `POST owner/stores/` |
| View or edit | `GET`/`PATCH owner/stores/{id}/` (multipart for `logo`) |
| Open or close | `PATCH owner/stores/{id}/` `{"status": "OPEN"}` or `{"status": "CLOSED"}` |

```json
{
  "id": 1,
  "store_name": "ABC Drinks",
  "description": "Soft drinks, water, and beer from Kariakoo.",
  "logo": null,
  "location": "Kariakoo Market, Uhuru Street, Dar es Salaam",
  "city": "Dar es Salaam",
  "area": "Kariakoo",
  "latitude": "-6.823490",
  "longitude": "39.274530",
  "phone": "+255713000001",
  "email": "abc@example.com",
  "status": "OPEN",
  "is_active": true,
  "delivery_fee": "2000.00",
  "created_at": "2026-10-07T21:12:23.547951+03:00",
  "updated_at": "2026-10-08T14:50:49.609487+03:00"
}
```

New stores start `CLOSED`: remind the owner to open the store. `is_active` is set by
an admin only; an inactive store disappears from customers.

#### Store-owner notifications

Same endpoints as the customer. Owners receive `ORDER_RECEIVED` ("New order …"),
`ORDER_CANCELLED` (when a customer cancels) and `LOW_STOCK`.

---

## 5. Features the backend does not support

| Feature you may see in a mockup | Status today | What the frontend should do |
| --- | --- | --- |
| Store ratings, reviews, stars | No data or endpoint | Hide them. Do not show fake ratings. |
| Opening hours, "opens at 8:00" | No hours; the owner toggles `OPEN`/`CLOSED` | Show "Open now" / "Closed" from `status`. |
| Global product search across all stores | Products are listed per store only | Search stores (`stores/?search=`), or filter stores by `category`. |
| Separate inventory module, stock history, suppliers | Stock is one number on the product | Use the products list, the stock endpoint and `?low_stock=true`. |
| Delivery or driver tracking, map with a moving rider, ETA | No drivers or delivery tracking; `ASSIGNED` and `OUT_FOR_DELIVERY` never happen | Show the status timeline; after READY the store completes the order itself. |
| Real-time updates (WebSockets, push, SMS) | In-app notifications only, no push | Poll as described in section 6. |
| Refunds, "request a refund" | Refunds are manual. A `REFUND_REQUIRED: …` note appears in `status_history` when money must be returned. `REFUNDED` is never set. | Show "Contact the store about your refund" when a paid order is rejected or cancelled. No refund button. |
| Card, bank, wallet payments | Checkout accepts CASH, MPESA, TIGO_PESA, AIRTEL_MONEY only | Offer these four only. |
| Real mobile-money prompts | Only a mock provider exists; prompts are simulated | In development, approve with the `simulate_mobile_money` command (README). |
| Ordering from several stores at once | A cart holds one store | Handle `CART_STORE_CONFLICT` with the "start a new cart" dialog. |
| Promo codes, discounts, loyalty points, tips | Not supported | Hide. |
| Scheduled delivery | Not supported | Hide. |
| Favourites or re-order | Not supported | Hide, or re-add items to the cart from an old order's `items` one by one. |
| Forgot password, change password, phone OTP | Not supported (no endpoint) | Hide; tell users to contact support. |
| Logout from all devices | No token revocation | Delete local tokens on logout. |
| Delete account | Not supported | Hide. |
| Category management, store approval, admin screens | Django admin only (`/admin/`); the API has just `admin/orders/{id}/cancel/` | Do not build admin screens yet. |

---

## 6. Frontend must / must not

**Must**

- Send `Authorization: Bearer <access>` on every protected call and refresh once on
  `401 TOKEN_INVALID`.
- Read `role` from `GET auth/me/` and show only that role's screens.
- Switch on `error.code` and show `details` for form fields.
- Render order buttons only from `allowed_actions`.
- Replace cart state with the response of every cart call, and show `cart.warnings`.
- Show money exactly as the server sends it (`"1500.00"` → `TSh 1,500`). Use
  `total_amount`, `subtotal`, `delivery_fee` and `line_total` from responses.
- Send money and coordinates as strings, and phones as `+255XXXXXXXXX`.
- Ask a reason before reject and any owner cancel.
- Poll instead of waiting for push:
  - payment status every 3 s while the payment screen is open, up to about 2 minutes;
  - order tracking every 15 to 30 s until the order is final;
  - the owner's PENDING orders every 15 to 30 s;
  - the unread notification count every 30 to 60 s.
- Stop polling when the screen is hidden or the order is final.
- Disable "Place order" and "Pay" while the request is in flight.
- Compress images to JPEG, PNG or WebP under 2 MB before upload.
- Treat a `404` on an object as "gone or not yours" and go back to the list.

**Must not**

- Calculate or send prices, totals, delivery fees or statuses; checkout ignores them.
- Show "Paid" for mobile money until `GET orders/{id}/payment/` says `SUCCESS`.
  The `pay/` response is only "prompt sent".
- Retry `POST orders/` automatically. On a network error, check `GET orders/` first;
  a second submit returns `EMPTY_CART`.
- Hard-code the transition table, enum labels from guesses, or role checks that the
  server does not make.
- Show `ASSIGNED`, `OUT_FOR_DELIVERY`, `REFUNDED`, `CARD` or `BANK` as options.
- Let a customer cancel after PENDING, or send `is_default` in an address body.
- Call `payments/webhook/…` from the app.
- Store passwords, or put demo passwords or any secret in the frontend repository.

---

## 7. Demo logins and TypeScript types

### Demo users

Load demo data with `docker compose exec backend python manage.py seed_demo`.
Passwords are **not** in this document or the code: they are read from the backend
`.env`. Ask the backend developer for the values; never commit them.

| Who | Phone | Password variable |
| --- | --- | --- |
| Customer (John Mushi) | `+255712345002` | `DEMO_CUSTOMER_PASSWORD` |
| ABC Drinks owner (Amina Hassan) | `+255712345003` | `DEMO_STORE_OWNER_PASSWORD` |
| Fresh Beverages owner (Neema Lyimo) | `+255712345004` | `DEMO_STORE_OWNER_PASSWORD` |
| Admin (Django admin only) | `+255712345001` | `DEMO_ADMIN_PASSWORD` |

Seeded data: 8 categories, two OPEN stores in Dar es Salaam (ABC Drinks in Kariakoo,
Fresh Beverages in Masaki) with 6 products each, and one saved "Home" address for the
customer.

To approve a mock mobile-money payment while testing, take the
`transaction_reference` from the `pay/` response and run
`docker compose exec backend python manage.py simulate_mobile_money <reference>`
(add `--fail` to decline). This needs `MOCK_PAYMENT_WEBHOOK_SECRET` set in `.env`.

### TypeScript types

Generate types from the committed contract with
[openapi-typescript](https://openapi-ts.dev/):

```bash
npx openapi-typescript ../docs/openapi.yaml -o src/api/schema.d.ts
```

```ts
import type { components, paths } from "./api/schema";

type OrderDetail = components["schemas"]["OrderDetail"];
type OrderStatus = components["schemas"]["OrderStatusEnum"];
type CartResponse =
  paths["/api/v1/cart/"]["get"]["responses"][200]["content"]["application/json"];
```

[openapi-fetch](https://openapi-ts.dev/openapi-fetch/) gives a typed client from the
same file. Regenerate the types whenever `docs/openapi.yaml` changes. The backend
regenerates it with:

```bash
docker compose exec backend python manage.py spectacular --file /app/openapi.yaml --validate --fail-on-warn
```

(then move `backend/openapi.yaml` to `docs/openapi.yaml`; the `docs` folder is not
mounted in the container).
