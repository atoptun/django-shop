from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.permissions import IsOwner
from apps.api.serializers.cart import (
    CartAddSerializer,
    CartItemSerializer,
    CartSerializer,
    CartUpdateSerializer,
)
from apps.cart.services import CartService


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsOwner]

    def list(self, request: Request):
        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)
        serializer = CartSerializer(cart_service.cart)
        return Response(serializer.data)

    def create(self, request: Request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        assert isinstance(validated_data, dict)
        product_id = validated_data["product_id"]
        quantity = validated_data["quantity"]

        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)

        try:
            cart_service.add(product_id, quantity)
            cart_item = cart_service.cart.items.get(product_id=product_id)  # type: ignore
            return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)
        except ValueError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["put", "delete"], url_path=r"items/(?P<product_id>\d+)")
    def items_detail(self, request: Request, product_id: str):
        product_id_int = int(product_id)
        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)

        if request.method == "PUT":
            serializer = CartUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            assert isinstance(validated_data, dict)
            quantity = validated_data["quantity"]
            try:
                new_qty = cart_service.update(product_id_int, quantity)
                return Response({"success": True, "quantity": new_qty}, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "DELETE":
            cart_service.remove(product_id_int)
            return Response(status=status.HTTP_204_NO_CONTENT)
