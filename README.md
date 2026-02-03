# Purchase Cart Service

Backend service that creates an order from a set of products and returns pricing and VAT information for the whole order and for each line item.

The implementation is intentionally small in scope, with the focus on structure, readability, correctness, and test quality.

---

## 1) Commands

### First-time setup

Bootstraps the local environment (builds containers, installs dependencies, runs migrations).

```bash
make setup
```

### Run locally with Docker

```bash
cp .env.example .env
./scripts/run.sh
```

### Load sample products (fixtures)

```bash
docker compose run --rm web python manage.py loaddata orders/fixtures/products.json
```

### Run tests

```bash
./scripts/tests.sh
```

### Coverage

```bash
docker compose run --rm web python -m pytest --cov=orders --cov-report=term-missing
```

### Useful one-liners

List products (SKU, id):

```bash
docker compose run --rm web python manage.py shell -c "from orders.models import Product; print(list(Product.objects.values_list('sku','id')))"
```

Create/apply migrations:

```bash
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate
```

---

## 2) Documentation

### API

#### Create an order

- Method: `POST`
- Path: `/orders/`

`currency` is optional and defaults to `EUR`.

Request body:

```json
{
  "items": [
    { "product_id": "00000000-0000-0000-0000-000000000000", "quantity": 2 },
    { "product_id": "11111111-1111-1111-1111-111111111111", "quantity": 1 }
  ],
  "currency": "EUR"
}
```

Example request:

```bash
curl -i -X POST http://localhost:8000/orders/   -H "Content-Type: application/json"   -d '{"items":[{"product_id":"00000000-0000-0000-0000-000000000000","quantity":2},{"product_id":"11111111-1111-1111-1111-111111111111","quantity":1}]}'
```

Response (example shape):

```json
{
  "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "currency": "EUR",
  "total_price": "37.20",
  "total_vat": "2.90",
  "items": [
    {
      "product": "00000000-0000-0000-0000-000000000000",
      "product_sku": "BOOK-001",
      "product_name": "Paperback Book",
      "quantity": 2,
      "unit_price_net": "12.90",
      "vat_rate": "0.0400",
      "unit_vat": "0.52",
      "line_price_net": "25.80",
      "line_vat": "1.03",
      "line_price_gross": "26.83"
    }
  ]
}
```

#### Retrieve an order

- Method: `GET`
- Path: `/orders/<id>/`

```bash
curl -i http://localhost:8000/orders/<ORDER_ID>/
```

### Calculation rules

- Money rounding: 2 decimals, half-up.
- VAT is calculated using **line-based rounding** (keeps item totals deterministic and auditable):
  - `line_price_net = round(unit_price_net * quantity)`
  - `line_vat = round(line_price_net * vat_rate)`
  - `line_price_gross = round(line_price_net + line_vat)`
- Order totals are the sum of the stored line values.

### Error cases (high level)

- Unknown or inactive product: `400`
- Empty items list: `400`

---

## 3) Domain model and order structure

### Product

Represents the current sellable catalog entry.

Key fields:

- `sku` (unique), `name`
- `unit_price_net` and `vat_rate` (current values)
- `active` flag

Assumption: products are created/managed out of band (fixtures or a separate backoffice/service). This API only consumes them.

### Order

Represents a checkout snapshot and aggregates totals.

Key fields:

- `currency`
- `total_price_net`, `total_vat`, `total_price_gross`
- `created_at`

Totals are stored explicitly to keep reads cheap and deterministic.

### OrderItem

Represents an order line. It snapshots product/pricing data at creation time.

Key fields:

- references: `order`, `product`
- snapshot: `product_sku`, `product_name`, `unit_price_net`, `vat_rate`
- computed: `unit_vat`, `line_price_net`, `line_vat`, `line_price_gross`

Design choice: the snapshot fields make historical orders stable even if product data changes later.

---

## 4) Design considerations

### Endpoint design

- The core use case is a single write operation: create an order from items and return the computed totals and breakdown.
- The create endpoint returns a full representation (including items) to support immediate UI/consumer needs.
- Duplicate products in the request are merged (same product id appears multiple times) to keep the write idempotent at the payload level and to align with the `(order, product)` uniqueness constraint.

### Pricing data

- Product holds the current price and VAT rate.
- Order items snapshot both raw values and computed line values.
- Why:
  - correct over time (price changes do not rewrite history)
  - simple reads (no joins to “current price” tables to render past orders)
  - predictable totals (totals are derived from stored line values, not recomputed later)

If a future version needs price history, the snapshot approach still holds: the order would select the “active” price at checkout time and then store it on the order item.

### Storage

- PostgreSQL is used as the primary data store because:
  - strong transactional guarantees (order creation is atomic)
  - constraints and indexes (data integrity and query performance)
  - reliable `Decimal` handling for monetary values
- Order creation is wrapped in a single transaction to avoid partial writes (e.g. order created without items).

### Orders and integrity

- Monetary values are stored as `Decimal` with fixed precision.
- VAT is computed line-based to avoid ambiguity and to keep the rules explicit in code/tests.
- Product deletion is protected to preserve historical integrity.
- Orders are append-only in this version (no updates/cancellations), which keeps the model simple and the test surface small.

### Tests

- API-level tests validate the full contract: status codes, response shape, totals, and per-item breakdown.
- Service-level tests cover business invariants (totals equal sum of lines), duplicate merge behavior, and transaction atomicity.

---

## 5) Technology choices

- **Python 3.11**: modern language features and solid ecosystem.
- **Django + Django REST Framework**: fast to build a clean REST API with validation and serialization, with a familiar structure for reviewers.
- **PostgreSQL**: relational consistency for orders + snapshots; good support for constraints and decimals.
- **Docker / Docker Compose**: reproducible setup for reviewers (no local DB required).
- **Pytest + pytest-django**: concise tests and good fixture support; enables both integration and service-level testing.
- **Ruff**: fast linting/formatting to keep style consistent.

---

## 6) Potential evolutions

- **Pricing & VAT versioning**: introduce a `ProductPrice` table with validity ranges (e.g. `valid_from`, `valid_to`) and pick the active row at checkout time. Orders would keep snapshotting values on `OrderItem` to preserve history.
  - If price history grows very large, **TimescaleDB** (PostgreSQL extension) can help with time-partitioning and faster “price at time T” queries.
- **Idempotency keys**: accept an idempotency key on `POST /orders/` to make client retries safe (avoid duplicates on timeouts).
- **Discounts/promotions**: add explicit fields on items and/or orders (discount net/VAT/gross) and include them in totals computation.
