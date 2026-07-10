from typing import Any, cast

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.permissions import IsOwner
from apps.api.serializers.orders import (
    OrderCreateSerializer,
    OrderSerializer,
)
from apps.api.serializers.payments import PaymentSubmitSchemaSerializer, PaymentSubmitSerializer
from apps.cart.services import CartService
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.exceptions import (
    InvalidPaymentMethodError,
    OrderAlreadyPaidError,
    PaymentAlreadyCompletedError,
    PaymentDeclinedError,
    PaymentProcessingInProgressError,
)
from apps.payments.models import Payment
from apps.payments.services import PaymentService


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."


class PaymentRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Payment Required."


@extend_schema(tags=["Orders"])
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

    @extend_schema(
        summary="List user orders",
        description=(
            "Retrieve a list of all orders placed by the authenticated user, "
            "ordered by creation date."
        ),
        responses={200: OrderSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        orders = Order.objects.filter(user=request.user).prefetch_related(
            "items__product", "payment"
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Retrieve order details",
        description="Retrieve detailed information about a specific order by its public UUID.",
        responses={200: OrderSerializer, 404: OpenApiResponse(description="Order not found")},
    )
    def retrieve(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.prefetch_related("items__product").get(
                uuid=uuid, user=request.user
            )
        except (Order.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @extend_schema(
        summary="Create an order",
        description=(
            "Create a new order containing all the items currently in the user's shopping cart."
        ),
        request=OrderCreateSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Invalid request or empty cart"),
        },
    )
    def create(self, request: Request) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        shipping_address = validated_data["shipping_address"]
        # payment_method = validated_data["payment_method"]

        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            raise serializers.ValidationError({"detail": "Your cart is empty."})

        try:
            order = OrderService.create_order(
                cart_service=cart_service,
                user=request.user,  # type: ignore
                shipping_address=shipping_address,
                # payment_method=payment_method,
            )

            order_prefetched = Order.objects.prefetch_related("items__product", "payment").get(
                pk=order.pk
            )
            return Response(OrderSerializer(order_prefetched).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    @extend_schema(
        summary="Cancel an order (DELETE)",
        description="Cancel a pending order. Returns 204 No Content upon successful cancellation.",
        responses={
            204: None,
            400: OpenApiResponse(description="Order cannot be cancelled"),
            404: OpenApiResponse(description="Order not found"),
        },
    )
    def destroy(self, request: Request, uuid: str) -> Response:
        order = self._get_cancellable_order(uuid, request.user)

        try:
            OrderService.cancel_order(order)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

    @extend_schema(
        methods=["POST"],
        summary="Pay for an order",
        description=("Submit payment details to process payment for a pending order. "),
        request=PaymentSubmitSchemaSerializer,
        responses={
            200: inline_serializer(
                name="PaymentSuccessResponse",
                fields={
                    "status": serializers.CharField(),
                    "payment_status": serializers.CharField(),
                    "transaction_id": serializers.CharField(),
                },
            ),
            202: inline_serializer(
                name="PaymentPendingResponse",
                fields={
                    "status": serializers.CharField(),
                    "payment_status": serializers.CharField(),
                    "transaction_id": serializers.CharField(required=False, allow_null=True),
                },
            ),
            400: OpenApiResponse(description="Bad request (already paid, invalid method)"),
            402: OpenApiResponse(description="Payment required (declined, insufficient funds)"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Conflict (payment processing in progress)"),
        },
    )
    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request: Request, uuid: str) -> Response:
        try:
            order = Order.objects.get(uuid=uuid, user=request.user)
        except (Order.DoesNotExist, ValueError) as e:
            raise NotFound("Order not found.") from e

        serializer = PaymentSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict, serializer.validated_data)
        payment_method_code = validated_data["payment_method_code"]
        payment_data = validated_data.get("payment_data", {})

        try:
            result = PaymentService.process_order_payment(order, payment_method_code, payment_data)

            if result["status"] == Payment.Status.COMPLETED:
                return Response(
                    {
                        "status": "success",
                        "payment_status": result["status"],
                        "transaction_id": result["transaction_id"],
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": "pending",
                        "payment_status": result["status"],
                        "transaction_id": result.get("transaction_id"),
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
        except (
            OrderAlreadyPaidError,
            PaymentAlreadyCompletedError,
            InvalidPaymentMethodError,
        ) as e:
            raise ValidationError({"detail": str(e)}) from e
        except PaymentProcessingInProgressError as e:
            raise Conflict(str(e)) from e
        except PaymentDeclinedError as e:
            raise PaymentRequired(str(e)) from e
