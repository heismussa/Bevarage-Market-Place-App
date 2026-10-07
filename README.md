# Beverage Delivery Marketplace

Django REST Framework backend for a beverage delivery marketplace. The database shape comes from [`docs/erd/beverage_delivery_erd_v2_1.dbml`](docs/erd/beverage_delivery_erd_v2_1.dbml). This repository currently contains the backend foundation only: the data model, Django admin, demo seed data, and phone/password authentication.

## Folder structure

```
backend/                 Django project (config) and apps
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

Phone numbers are stored as `+255` followed by 9 digits, for example `+255712345678`.

## Tests

Tests run against PostgreSQL inside Docker. Partial unique indexes and check constraints are enforced by the database, so do not point the test run at SQLite.

```bash
docker compose exec backend python manage.py test
```
