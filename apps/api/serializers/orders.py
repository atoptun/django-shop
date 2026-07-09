from rest_framework import serializers

from apps.api.serializers.products import ProductListSerializer
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentMethod


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price", "subtotal"]

    def get_subtotal(self, obj: OrderItem) -> str:
        return f"{obj.subtotal:.2f}"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
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
    payment_method_id = serializers.IntegerField()

    def validate_payment_method_id(self, value: int) -> int:
        if not PaymentMethod.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive payment method.")
        return value


class OrderUpdateSerializer(serializers.Serializer):
    status = serializers.CharField()

    def validate_status(self, value: str) -> str:
        if value.lower() != "cancelled":
            raise serializers.ValidationError("Only 'cancelled' status changes are allowed.")
        return value.lower()
