from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse

from orders.models import Order, OrderItem, Product
from orders.tests.conftest import money


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
    p1_gross = money(p1_net + p1_vat)

    p2_net = money(p2.unit_price_net * 1)
    p2_vat = money(p2_net * p2.vat_rate)
    p2_gross = money(p2_net + p2_vat)

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

    by_sku = {i["product_sku"]: i for i in data["items"]}
    assert set(by_sku.keys()) == {"TEST-BOOK-001", "TEST-ELEC-001"}

    book = by_sku["TEST-BOOK-001"]
    assert Decimal(book["line_price_net"]) == p1_net
    assert Decimal(book["line_vat"]) == p1_vat
    assert Decimal(book["line_price_gross"]) == p1_gross

    cable = by_sku["TEST-ELEC-001"]
    assert Decimal(cable["line_price_net"]) == p2_net
    assert Decimal(cable["line_vat"]) == p2_vat
    assert Decimal(cable["line_price_gross"]) == p2_gross


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

    item = data["items"][0]
    assert item["product_sku"] == "TEST-ROUND-001"
    assert Decimal(item["line_price_net"]) == Decimal("2.97")
    assert Decimal(item["line_vat"]) == Decimal("0.65")
    assert Decimal(item["line_price_gross"]) == Decimal("3.62")


@pytest.mark.django_db
def test_create_order_unknown_product_returns_400(client):
    resp = client.post(
        reverse("order-create"),
        data={"items": [{"product_id": str(uuid4()), "quantity": 1}]},
        format="json",
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_order_rejects_empty_items(client):
    resp = client.post(reverse("order-create"), data={"items": []}, format="json")
    assert resp.status_code == 400
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0


@pytest.mark.django_db
def test_create_order_rejects_inactive_product(client, product_factory):
    p = product_factory(sku="MORE-INACT-001", active=False)

    resp = client.post(
        reverse("order-create"),
        data={"items": [{"product_id": str(p.id), "quantity": 1}]},
        format="json",
    )

    assert resp.status_code == 400
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0


@pytest.mark.django_db
def test_create_order_merges_duplicate_product_ids(client, product_factory):
    p = product_factory(sku="MORE-DUP-001", unit_price_net=Decimal("5.00"), vat_rate=Decimal("0.2200"))

    resp = client.post(
        reverse("order-create"),
        data={
            "items": [
                {"product_id": str(p.id), "quantity": 1},
                {"product_id": str(p.id), "quantity": 2},
            ]
        },
        format="json",
    )

    assert resp.status_code == 201
    data = resp.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3

    line_net = money(p.unit_price_net * 3)
    line_vat = money(line_net * p.vat_rate)
    line_gross = money(line_net + line_vat)

    assert Decimal(data["total_vat"]) == line_vat
    assert Decimal(data["total_price"]) == line_gross


@pytest.mark.django_db
def test_order_items_snapshot_is_stable_after_product_change(client, product_factory):
    p = product_factory(
        sku="MORE-SNAP-001",
        name="Initial Name",
        unit_price_net=Decimal("12.90"),
        vat_rate=Decimal("0.0400"),
    )

    create_resp = client.post(
        reverse("order-create"),
        data={"items": [{"product_id": str(p.id), "quantity": 2}]},
        format="json",
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    p.name = "Updated Name"
    p.unit_price_net = Decimal("99.99")
    p.vat_rate = Decimal("0.2200")
    p.save(update_fields=["name", "unit_price_net", "vat_rate"])

    detail_resp = client.get(reverse("order-detail", kwargs={"pk": order_id}))
    assert detail_resp.status_code == 200
    data = detail_resp.json()

    assert data["id"] == order_id
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["product_sku"] == "MORE-SNAP-001"
    assert item["product_name"] == "Initial Name"
    assert Decimal(item["unit_price_net"]) == Decimal("12.90")
    assert Decimal(item["vat_rate"]) == Decimal("0.0400")

    assert Decimal(item["line_price_net"]) == Decimal("25.80")
    assert Decimal(item["line_vat"]) == Decimal("1.03")
    assert Decimal(item["line_price_gross"]) == Decimal("26.83")


@pytest.mark.django_db
def test_order_detail_unknown_id_returns_404(client):
    resp = client.get(reverse("order-detail", kwargs={"pk": uuid4()}))
    assert resp.status_code == 404
