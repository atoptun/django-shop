from collections import defaultdict

import django_filters
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.products.models import Category, Product

from ..serializers.products import CategorySerializer, ProductListSerializer


@extend_schema(
    tags=["Products"],
    description="API view set for listing and retrieving categories.",
)
class CategoryAPIViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    lookup_field = "slug"
    serializer_class = CategorySerializer

    permission_classes = [AllowAny]

    filter_backends = []
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        all_cats: list[Category] = list(queryset)

        children_map = defaultdict(list)
        roots = []
        for cat in all_cats:
            if cat.parent_id is None:
                roots.append(cat)
            else:
                children_map[cat.parent_id].append(cat)

        page = self.paginate_queryset(roots)
        context = self.get_serializer_context()
        context["children_map"] = children_map

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(roots, many=True, context=context)
        return Response(serializer.data)


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr="gte")
    category_slug = django_filters.CharFilter(field_name="category__slug")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category"]

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset


@extend_schema(
    tags=["Products"],
    description="API view set for listing and retrieving products.",
)
@method_decorator(
    name="list",
    decorator=extend_schema(
        parameters=[
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sorting options for the results.",
                enum=[
                    "price",
                    "-price",
                    "average_rating",
                    "-average_rating",
                    "created_at",
                    "-created_at",
                ],
            )
        ]
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("category")
    lookup_field = "slug"
    serializer_class = ProductListSerializer

    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter

    search_fields = ["name", "description"]
    ordering_fields = ["price", "average_rating", "created_at"]
    ordering = ["-created_at"]
