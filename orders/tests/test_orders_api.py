from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Product

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_create_order_returns_totals_and_items(client):
    p1 = Product.objects.create(
        sku="TEST-BOOK-001",
        name="Test Book",
        unit_price_net=Decimal("12.90"),
        vat_rate=Decimal("0.0400"),
        active=True,
    )
    p2 = Product.objects.create(
        sku="TEST-ELEC-001",
        name="Test Cable",
        unit_price_net=Decimal("8.50"),
        vat_rate=Decimal("0.2200"),
        active=True,
    )

    items = [
        {"product_id": str(p1.id), "quantity": 2},
        {"product_id": str(p2.id), "quantity": 1},
    ]

    p1_net = money(p1.unit_price_net * 2)
    p1_vat = money(p1_net * p1.vat_rate)

    p2_net = money(p2.unit_price_net * 1)
    p2_vat = money(p2_net * p2.vat_rate)

    total_net = money(p1_net + p2_net)
    total_vat = money(p1_vat + p2_vat)
    total_gross = money(total_net + total_vat)

    resp = client.post(reverse("order-create"), data={"items": items}, format="json")
    assert resp.status_code == 201

    data = resp.json()
    assert "id" in data
    assert data["currency"] == "EUR"
    assert Decimal(data["total_price"]) == total_gross
    assert Decimal(data["total_vat"]) == total_vat
    assert len(data["items"]) == 2

    skus = {i["product_sku"] for i in data["items"]}
    assert skus == {"TEST-BOOK-001", "TEST-ELEC-001"}


@pytest.mark.django_db
def test_create_order_rounding_line_vat(client):
    p = Product.objects.create(
        sku="TEST-ROUND-001",
        name="Rounding Product",
        unit_price_net=Decimal("0.99"),
        vat_rate=Decimal("0.2200"),
        active=True,
    )

    resp = client.post(
        reverse("order-create"),
        data={"items": [{"product_id": str(p.id), "quantity": 3}]},
        format="json",
    )

    assert resp.status_code == 201
    data = resp.json()

    assert Decimal(data["total_vat"]) == Decimal("0.65")
    assert Decimal(data["total_price"]) == Decimal("3.62")
    assert len(data["items"]) == 1


@pytest.mark.django_db
def test_create_order_unknown_product_returns_400(client):
    resp = client.post(
        reverse("order-create"),
        data={"items": [{"product_id": str(uuid4()), "quantity": 1}]},
        format="json",
    )

    assert resp.status_code == 400
