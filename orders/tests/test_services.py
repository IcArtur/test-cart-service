from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from orders.models import Order, OrderItem
from orders.services import create_order
from orders.tests.conftest import money


@pytest.mark.django_db
def test_create_order_service_merges_duplicate_items(product_factory):
    p = product_factory(unit_price_net=Decimal("5.00"), vat_rate=Decimal("0.2200"))

    order = create_order(
        items=[
            {"product_id": p.id, "quantity": 1},
            {"product_id": p.id, "quantity": 2},
        ],
        currency="EUR",
    )

    assert order.items.count() == 1
    item = order.items.get()
    assert item.quantity == 3

    expected_net = money(Decimal("5.00") * 3)
    expected_vat = money(expected_net * Decimal("0.2200"))
    expected_gross = money(expected_net + expected_vat)

    assert item.line_price_net == expected_net
    assert item.line_vat == expected_vat
    assert item.line_price_gross == expected_gross


@pytest.mark.django_db
def test_create_order_service_totals_match_sum_of_items(product_factory):
    p1 = product_factory(unit_price_net=Decimal("12.90"), vat_rate=Decimal("0.0400"))
    p2 = product_factory(unit_price_net=Decimal("8.50"), vat_rate=Decimal("0.2200"))

    order = create_order(
        items=[
            {"product_id": p1.id, "quantity": 2},
            {"product_id": p2.id, "quantity": 1},
        ],
        currency="EUR",
    )

    items = list(order.items.all())

    sum_net = money(sum((i.line_price_net for i in items), Decimal("0.00")))
    sum_vat = money(sum((i.line_vat for i in items), Decimal("0.00")))
    sum_gross = money(sum_net + sum_vat)

    assert order.total_price_net == sum_net
    assert order.total_vat == sum_vat
    assert order.total_price_gross == sum_gross


@pytest.mark.django_db
def test_create_order_service_is_atomic_on_failure(monkeypatch, product_factory):
    p = product_factory(unit_price_net=Decimal("10.00"), vat_rate=Decimal("0.2200"))

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(OrderItem.objects, "bulk_create", boom)

    with pytest.raises(RuntimeError):
        create_order(items=[{"product_id": p.id, "quantity": 1}], currency="EUR")

    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
