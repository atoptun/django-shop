from rest_framework import serializers

from apps.api.serializers.products import ProductListSerializer
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentMethod


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "uuid",
            "status",
            "total_price",
            "shipping_address",
            "created_at",
            "updated_at",
            "items",
        ]


class OrderCreateSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(max_length=500)
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.filter(is_active=True)
    )


class OrderUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["cancelled"])
