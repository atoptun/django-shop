from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
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


@extend_schema(tags=["Cart"])
class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsOwner]

    @extend_schema(
        summary="Retrieve shopping cart",
        description=(
            "Retrieve the active user's shopping cart details, "
            "including items list, quantities, and totals."
        ),
        responses={200: CartSerializer},
    )
    def list(self, request: Request):
        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)
        serializer = CartSerializer(cart_service.cart)
        return Response(serializer.data)

    @extend_schema(
        summary="Add product to cart",
        description=(
            "Add a product to the user's shopping cart, specifying quantity. "
            "If already present, quantity is incremented."
        ),
        request=CartAddSerializer,
        responses={201: CartItemSerializer, 400: OpenApiResponse(description="Bad request")},
    )
    def create(self, request: Request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        assert isinstance(validated_data, dict)
        product_slug = validated_data["product_slug"]
        quantity = validated_data["quantity"]

        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)

        try:
            cart_service.add(product_slug, quantity)
            cart_item = cart_service.cart.items.get(product__slug=product_slug)  # type: ignore
            return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)
        except ValueError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["PUT"],
        summary="Update cart item quantity",
        description="Change the quantity of a product currently inside the user's cart.",
        request=CartUpdateSerializer,
        responses={
            200: inline_serializer(
                name="CartItemUpdateResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "quantity": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="Bad request"),
        },
    )
    @extend_schema(
        methods=["DELETE"],
        summary="Remove product from cart",
        description="Delete a product from the user's shopping cart entirely.",
        responses={204: None},
    )
    @action(detail=False, methods=["put", "delete"], url_path=r"items/(?P<product_slug>[-\w]+)")
    def items_detail(self, request: Request, product_slug: str):
        cart_service = CartService(request)
        self.check_object_permissions(request, cart_service.cart)

        if request.method == "PUT":
            serializer = CartUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            assert isinstance(validated_data, dict)
            quantity = validated_data["quantity"]
            try:
                new_qty = cart_service.update(product_slug, quantity)
                return Response({"success": True, "quantity": new_qty}, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "DELETE":
            cart_service.remove(product_slug)
            return Response(status=status.HTTP_204_NO_CONTENT)
