import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from apps.products.models import Category, Product

from ..serializers.products import CategorySerializer, ProductListSerializer


@extend_schema(tags=["Products"])
class CategoryAPIViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for listing and retrieving categories."""

    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr="gte")
    category_slug = django_filters.CharFilter(field_name="category__slug")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category", "is_active"]

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset


@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for listing and retrieving products."""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter

    search_fields = ["name", "description"]
    ordering_fields = ["price", "average_rating", "created_at"]
    ordering = ["-created_at"]
