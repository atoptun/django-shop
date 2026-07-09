from typing import cast

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.serializers.reviews import ReviewCreateSerializer, ReviewSerializer
from apps.products.models import Product
from apps.reviews.services import ReviewService


class ReviewViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["create", "can_review"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def list(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        service = ReviewService(request)
        reviews = service.get_reviews_for_product(product)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

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

    def can_review(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        service = ReviewService(request)
        user_can_review = service.can_user_review_product(product)
        already_reviewed = service.user_already_reviewed_product(product)

        return Response(
            {"can_review": user_can_review, "already_reviewed": already_reviewed},
            status=status.HTTP_200_OK,
        )
