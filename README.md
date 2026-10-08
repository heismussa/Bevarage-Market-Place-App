# Beverage Delivery Marketplace

Django REST Framework backend for a beverage delivery marketplace. The database shape comes from [`docs/erd/beverage_delivery_erd_v2_1.dbml`](docs/erd/beverage_delivery_erd_v2_1.dbml). This repository currently contains the backend foundation only: the data model, Django admin, demo seed data, and phone/password authentication.

## Folder structure

```
backend/                 Django project (config) and apps
  core/                  Shared plumbing: errors, pagination, ownership, test helpers
  accounts/              User, Customer, StoreOwner, Address, auth API
  stores/                Store
  catalog/               Category, Product
  cart/                  Cart, CartItem
  orders/                Order, OrderItem, OrderStatusHistory
  payments/              Payment
  notifications/         Notification
frontend/                Empty. Reserved for the client.
docs/erd/                DBML source of truth
docker-compose.yml
.env.example
```

Driver and Delivery tables are in the ERD for later and are not implemented.

## Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Copy the environment file and replace the placeholders:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell: `Copy-Item .env.example .env`

   `POSTGRES_PASSWORD` and the password inside `DATABASE_URL` must match. Demo passwords are read from `DEMO_ADMIN_PASSWORD`, `DEMO_CUSTOMER_PASSWORD`, and `DEMO_STORE_OWNER_PASSWORD`.
3. Start the database and the API:

   ```bash
   docker compose up --build
   ```

   The API listens on <http://localhost:8000>. On startup the backend applies migrations to PostgreSQL.

## Commands

| Task | Command |
| --- | --- |
| Start the stack | `docker compose up --build` |
| Apply migrations | `docker compose exec backend python manage.py migrate` |
| Create an admin user | `docker compose exec backend python manage.py createsuperuser` |
| Load demo data | `docker compose exec backend python manage.py seed_demo` |
| Run tests | `docker compose exec backend python manage.py test` |
| Lint | `docker compose exec backend ruff check .` |
| Format | `docker compose exec backend ruff format .` |
| Check for missing migrations | `docker compose exec backend python manage.py makemigrations --check --dry-run` |
| Validate the OpenAPI schema | `docker compose exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml` |
| Stop the stack | `docker compose down` |

`seed_demo` is safe to run twice. It will not duplicate rows and it will not reset passwords that were already set.

Demo phones after seeding:

| Who | Phone |
| --- | --- |
| Admin (Django admin) | +255712345001 |
| Customer | +255712345002 |
| ABC Drinks owner | +255712345003 |
| Fresh Beverages owner | +255712345004 |

Both store owners use `DEMO_STORE_OWNER_PASSWORD`.

## URLs

- Health: `GET /api/v1/health/` → `{"status": "ok"}`
- API docs: <http://localhost:8000/api/docs/>
- OpenAPI schema: <http://localhost:8000/api/schema/>
- Django admin: <http://localhost:8000/admin/>
- `POST /api/v1/auth/register/` with `full_name`, `phone`, `password`, optional `email`, and `role` (`CUSTOMER` or `STORE_OWNER`)
- `POST /api/v1/auth/login/` with `phone` and `password`
- `POST /api/v1/auth/refresh/` with `refresh`
- `GET` and `PATCH /api/v1/auth/me/` with `Authorization: Bearer <access>`

The full endpoint list, with examples, is in the API docs. A short map by area:

| Area | Endpoints | Who |
| --- | --- | --- |
| Catalog | `categories/`, `stores/`, `stores/{id}/`, `stores/{id}/products/`, `products/{id}/` | Anyone |
| Owner stores | `owner/stores/`, `owner/stores/{id}/` | Store owner |
| Owner products | `owner/stores/{store_id}/products/`, `owner/products/{id}/`, `owner/products/{id}/stock/` | Store owner |
| Addresses | `addresses/`, `addresses/{id}/`, `addresses/{id}/set-default/` | Customer |
| Cart | `cart/`, `cart/items/`, `cart/items/{id}/` | Customer |
| Orders | `orders/`, `orders/{id}/`, `orders/{id}/cancel/` | Customer |
| Admin orders | `admin/orders/{id}/cancel/` | Admin |

The roadmap and business rules for each stage are in [`docs/BACKEND_PLAN.md`](docs/BACKEND_PLAN.md).

Phone numbers are stored as `+255` followed by 9 digits, for example `+255712345678`.

## Tests

Tests run against PostgreSQL inside Docker. Partial unique indexes and check constraints are enforced by the database, so do not point the test run at SQLite.

```bash
docker compose exec backend python manage.py test
```

The Docker image installs `requirements-dev.txt` (factory_boy, ruff) on top of `requirements.txt`. A production image can be built with the default `REQUIREMENTS_FILE=requirements.txt`.

## API conventions

These apply to every endpoint. The shared code lives in `backend/core/`.

### Error format

Every error response has the same body:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "This field is required.", "details": {"phone": ["This field is required."]}}}
```

- `code` is stable and machine-readable. Codes are listed in `core/errors.py` (`ErrorCode`). New codes may be added. Existing codes are never renamed or reused.
- `message` is a human-readable sentence. For validation errors it is the first field error.
- `details` is always an object. Validation errors put field errors here.
- Services raise `core.errors.ApiError(code, message, status_code=..., details=...)` for business errors, for example `CART_STORE_CONFLICT` with status 409.
- Unknown `/api/` URLs and unexpected server errors also use this format (`NOT_FOUND`, `INTERNAL_ERROR`). Internal error messages never include exception text.

| Status | Code |
| --- | --- |
| 400 | `VALIDATION_ERROR`, `PARSE_ERROR` |
| 401 | `NOT_AUTHENTICATED`, `AUTHENTICATION_FAILED`, `TOKEN_INVALID` |
| 403 | `PERMISSION_DENIED` |
| 404 | `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `CONFLICT`, `CART_STORE_CONFLICT`, `PRODUCT_UNAVAILABLE`, `STORE_CLOSED`, `INSUFFICIENT_STOCK`, `EMPTY_CART`, `INVALID_TRANSITION` |
| 429 | `THROTTLED` (`details.wait_seconds`) |
| 500 | `INTERNAL_ERROR` |

### Permissions and ownership

- The default permission is `core.permissions.DenyAll`. Every view must declare `permission_classes` explicitly.
- Role checks use `IsCustomer`, `IsStoreOwner`, and `IsAdminRole` from `accounts/permissions.py`. A wrong role gets 403 `PERMISSION_DENIED`.
- Object ownership is enforced by filtering the queryset, so another user's object returns 404 `NOT_FOUND`, never 403. Use `core.ownership.OwnerScopedQuerysetMixin` with `owner_field = OwnerField.CUSTOMER` (or `STORE_OWNER`, `STORE_OF_OBJECT`, `USER`), or `get_owned_or_404(...)` inside services.
- `get_customer_profile(user)` and `get_store_owner_profile(user)` return the profile or raise 403.

### Lists

- Pagination: `?page=N&page_size=M`, default 20, maximum 100. The response is `{"count", "next", "previous", "results"}`.
- Filtering uses django-filter (`filterset_class`), plus `?search=` and `?ordering=` where a view enables them.
- Every list view uses `select_related` and `prefetch_related` and has an `assertNumQueries` test.

### Code layout

- Views stay thin. Business logic lives in each app's `services.py`. Serializers only validate and shape data.
- Money is always `Decimal`. Prices and totals are recomputed on the server from the database.
- Every endpoint has `extend_schema` with tags, request, response, error responses (`core.schema.standard_errors(400, 401, ...)` or `error_response(...)`), and examples.

### Writing tests

- Factories for every model are in `core/testing/factories.py`. All test users have the password `TEST_PASSWORD`.
- `core.testing.api.ApiTestCase` gives you authenticated clients with a real JWT, and an error assertion:

```python
from core.errors import ErrorCode
from core.testing.api import ApiTestCase


class ExampleTests(ApiTestCase):
    def test_other_customer_gets_404(self):
        client, customer = self.customer_client()       # also: store_owner_client(), admin_client()
        response = client.get("/api/v1/some-object/999/")
        self.assertError(response, 404, ErrorCode.NOT_FOUND)
```
