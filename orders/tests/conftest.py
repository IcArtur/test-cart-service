from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from orders.models import Product

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def product_factory(db):
    def create(**overrides):
        defaults = {
            "sku": f"TEST-{uuid4().hex[:10].upper()}",
            "name": "Default Product",
            "unit_price_net": Decimal("1.00"),
            "vat_rate": Decimal("0.2200"),
            "active": True,
        }
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    return create
