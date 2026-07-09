from rest_framework import serializers, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.permissions import IsOwner
from apps.api.serializers.orders import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderUpdateSerializer,
)
from apps.cart.services import CartService
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.models import PaymentMethod


class OrderViewSet(viewsets.ViewSet):
    permission_classes = [IsOwner]
    lookup_field = "uuid"
    lookup_value_regex = r"[0-9a-f-]{36}"

    def list(self, request: Request) -> Response:
        orders = Order.objects.filter(user=request.user).prefetch_related("items__product")
        for order in orders:
            self.check_object_permissions(request, order)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.prefetch_related("items__product").get(uuid=uuid)
        except (Order.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, order)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def create(self, request: Request) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        assert isinstance(validated_data, dict)
        shipping_address = validated_data["shipping_address"]
        payment_method_id = validated_data["payment_method_id"]

        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            raise serializers.ValidationError({"detail": "Your cart is empty."})

        payment_method = PaymentMethod.objects.get(id=payment_method_id)

        try:
            order = OrderService.create_order(
                cart_service=cart_service,
                user=request.user,  # type: ignore
                shipping_address=shipping_address,
                payment_method=payment_method,
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    def update(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.get(uuid=uuid)
        except (Order.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, order)

        serializer = OrderUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            OrderService.cancel_order(order)
            order.refresh_from_db()
            return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    def destroy(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.get(uuid=uuid)
        except (Order.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, order)

        try:
            OrderService.cancel_order(order)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e
