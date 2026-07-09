from typing import Any, cast

from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
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


class OrderViewSet(viewsets.ViewSet):
    permission_classes = [IsOwner]
    lookup_field = "uuid"
    lookup_value_regex = (
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    def _get_cancellable_order(self, uuid: str, user: Any) -> Order:
        try:
            order = Order.objects.get(uuid=uuid, user=user)
        except (Order.DoesNotExist, ValueError) as e:
            raise NotFound() from e

        if order.status != Order.Status.PENDING:
            raise ValidationError({"detail": "Only pending orders can be cancelled."})
        return order

    def list(self, request: Request) -> Response:
        orders = Order.objects.filter(user=request.user).prefetch_related("items__product")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.prefetch_related("items__product").get(
                uuid=uuid, user=request.user
            )
        except (Order.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def create(self, request: Request) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        shipping_address = validated_data["shipping_address"]
        payment_method = validated_data["payment_method"]

        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            raise serializers.ValidationError({"detail": "Your cart is empty."})

        try:
            order = OrderService.create_order(
                cart_service=cart_service,
                user=request.user,  # type: ignore
                shipping_address=shipping_address,
                payment_method=payment_method,
            )

            order_prefetched = Order.objects.prefetch_related("items__product").get(pk=order.pk)
            return Response(OrderSerializer(order_prefetched).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    def update(self, request: Request, uuid: str) -> Response:
        order = self._get_cancellable_order(uuid, request.user)

        serializer = OrderUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            OrderService.cancel_order(order)

            order_prefetched = Order.objects.prefetch_related("items__product").get(pk=order.pk)
            return Response(OrderSerializer(order_prefetched).data, status=status.HTTP_200_OK)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    def destroy(self, request: Request, uuid: str) -> Response:
        order = self._get_cancellable_order(uuid, request.user)

        try:
            OrderService.cancel_order(order)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e
