import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)

    unit_price_net = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0.0000")),
            MaxValueValidator(Decimal("1.0000")),
        ],
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["active"]),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    currency = models.CharField(max_length=3, default="EUR")
    total_price_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_vat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_price_gross = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return str(self.id)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    product_sku = models.CharField(max_length=64)
    product_name = models.CharField(max_length=255)

    unit_price_net = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0.0000")),
            MaxValueValidator(Decimal("1.0000")),
        ],
    )

    unit_vat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_price_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_vat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_price_gross = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="uniq_order_product"),
        ]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.order_id} - {self.product_sku} x{self.quantity}"
