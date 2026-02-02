# Purchase Cart Service

This repository contains a small backend service implementing a simplified purchase cart.

The service exposes a REST API that allows creating an order from a set of products and returns pricing and VAT information at both order and item level.

The focus of the project is on code structure, correctness, and testability.

## Tech stack

- Python 3.11
- Django
- Django REST Framework
- PostgreSQL
- Docker / Docker Compose

## Configuration

The application is configured via environment variables.  
An example configuration is available in `.env.example`.

## Running the service

```bash
./scripts/run.sh

The API will be available at:

http://localhost:8000

Running tests

./scripts/tests.sh

Notes

    Prices and VAT are calculated at order creation time

    Pricing data is snapshotted to preserve historical consistency

    Order creation is handled atomically
```
