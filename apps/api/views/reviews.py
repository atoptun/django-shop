from typing import cast

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.serializers.reviews import ReviewCreateSerializer, ReviewSerializer
from apps.products.models import Product
from apps.reviews.services import ReviewService


@extend_schema(
    tags=["Product Reviews"],
    description="API view set for managing product reviews.",
)
class ReviewViewSet(viewsets.ViewSet):
    pagination_class = PageNumberPagination

    def get_permissions(self):
        if self.action in ["create", "can_review"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    @extend_schema(
        summary="List approved product reviews",
        description=(
            "Retrieve a list of approved reviews for the product identified by slug, "
            "sorted by creation date (newest first)."
        ),
        responses={200: ReviewSerializer(many=True)},
    )
    def list(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        service = ReviewService(request)
        reviews = service.get_reviews_for_product(product)

        paginator = self.pagination_class()
        paginated_reviews = paginator.paginate_queryset(reviews, request, view=self)
        if paginated_reviews is not None:
            serializer = ReviewSerializer(paginated_reviews, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Submit a review for a product",
        description=(
            "Submit a new review for the product. Only authenticated users "
            "who purchased the product and haven't reviewed it yet can submit. "
            "The review will be created as 'pending'."
        ),
        request=ReviewCreateSerializer,
        responses={
            201: ReviewSerializer,
            400: OpenApiResponse(description="Invalid input or duplicate review"),
            403: OpenApiResponse(description="User did not purchase the product"),
        },
    )
    def create(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        service = ReviewService(request)

        if not service.can_user_review_product(product):
            raise PermissionDenied("You must purchase the product before reviewing it.")

        if service.user_already_reviewed_product(product):
            raise serializers.ValidationError({"detail": "You have already reviewed this product."})

        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict, serializer.validated_data)
        rating = validated_data["rating"]
        comment = validated_data.get("comment", "")

        review = service.create_review(
            product=product,
            rating=rating,
            comment=comment,
        )

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Check if user can review a product",
        description=(
            "Returns whether the active user has purchased this product (can review) "
            "and if they have already reviewed it."
        ),
        responses={
            200: inline_serializer(
                name="CanReviewResponse",
                fields={
                    "can_review": serializers.BooleanField(),
                    "already_reviewed": serializers.BooleanField(),
                },
            )
        },
    )
    def can_review(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        service = ReviewService(request)
        user_can_review = service.can_user_review_product(product)
        already_reviewed = service.user_already_reviewed_product(product)

        return Response(
            {"can_review": user_can_review, "already_reviewed": already_reviewed},
            status=status.HTTP_200_OK,
        )
