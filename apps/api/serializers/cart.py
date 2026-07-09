from rest_framework import serializers

from apps.api.serializers.products import ProductListSerializer
from apps.cart.models import Cart, CartItem
from apps.products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_items", "total_price"]

    def get_total_items(self, obj: Cart) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj: Cart) -> str:
        total = sum(item.subtotal for item in obj.items.all())
        return f"{total:.2f}"


class CartAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value: int) -> int:
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist.")
        return value

    def validate(self, attrs: dict) -> dict:
        product_id = attrs["product_id"]
        quantity = attrs["quantity"]
        product = Product.objects.get(id=product_id)
        if quantity > product.stock:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} items are available in stock."}
            )
        return attrs


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
