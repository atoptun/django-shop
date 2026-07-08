from collections import defaultdict

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.products.models import Category, Product

from ..serializers.products import CategorySerializer, ProductListSerializer


@extend_schema(tags=["Products"])
class CategoryAPIViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for listing and retrieving categories."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        """List categories with their children in a hierarchical structure."""

        all_cats: list[Category] = list(self.get_queryset())

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


@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for listing and retrieving products."""

    queryset = Product.objects.filter(is_active=True).select_related("category")
    serializer_class = ProductListSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter

    search_fields = ["name", "description"]
    ordering_fields = ["price", "average_rating", "created_at"]
    ordering = ["-created_at"]
