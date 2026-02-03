from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from orders.models import Order, OrderItem, Product

_MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY, rounding=ROUND_HALF_UP)


@transaction.atomic
def create_order(*, items: list[dict], currency: str = "EUR") -> Order:
    if not items:
        raise ValidationError({"items": "This field is required."})

    quantities = defaultdict(int)
    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        if quantity < 1:
            raise ValidationError({"items": "Quantity must be >= 1."})
        quantities[product_id] += quantity

    products = {p.id: p for p in Product.objects.filter(id__in=quantities.keys(), active=True)}
    if len(products) != len(quantities):
        raise ValidationError({"items": "One or more products do not exist or are inactive."})

    order = Order.objects.create(currency=currency)

    total_net = Decimal("0.00")
    total_vat = Decimal("0.00")

    order_items: list[OrderItem] = []

    for product_id, quantity in quantities.items():
        product = products[product_id]

        unit_price_net = product.unit_price_net
        vat_rate = product.vat_rate

        unit_vat = _money(unit_price_net * vat_rate)
        line_net = _money(unit_price_net * quantity)

        line_vat = _money(line_net * vat_rate)
        line_gross = _money(line_net + line_vat)

        total_net = _money(total_net + line_net)
        total_vat = _money(total_vat + line_vat)

        order_items.append(
            OrderItem(
                order=order,
                product=product,
                quantity=quantity,
                product_sku=product.sku,
                product_name=product.name,
                unit_price_net=unit_price_net,
                vat_rate=vat_rate,
                unit_vat=unit_vat,
                line_price_net=line_net,
                line_vat=line_vat,
                line_price_gross=line_gross,
            )
        )

    OrderItem.objects.bulk_create(order_items)

    order.total_price_net = total_net
    order.total_vat = total_vat
    order.total_price_gross = _money(total_net + total_vat)
    order.save(update_fields=["total_price_net", "total_vat", "total_price_gross"])

    return Order.objects.prefetch_related("items").get(pk=order.pk)
