from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from orders.models import Order, OrderItem
from orders.services import create_order


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)
    currency = serializers.CharField(required=False, default="EUR", max_length=3)

    def create(self, validated_data):
        try:
            return create_order(items=validated_data["items"], currency=validated_data["currency"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "product",
            "product_sku",
            "product_name",
            "quantity",
            "unit_price_net",
            "vat_rate",
            "unit_vat",
            "line_price_net",
            "line_vat",
            "line_price_gross",
        ]


class OrderSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(source="total_price_gross", max_digits=12, decimal_places=2)
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "currency",
            "total_price",
            "total_vat",
            "items",
        ]
