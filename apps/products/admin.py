from django.contrib import admin
from django.db.models import Avg, Count
from django.db.models.query import QuerySet
from django.http import HttpRequest

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = ["name", "slug", "parent", "created_at", "deleted"]
    search_fields = ["name", "slug"]
    list_filter = ["parent"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted"]
    fields = ["name", "slug", "parent", "created_at", "updated_at", "deleted"]


@admin.register(Product)
class ProductAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = [
        "name",
        "slug",
        "category",
        "price",
        "price_tag",
        "stock",
        "is_active",
        "average_rating",
        "created_at",
        "updated_at",
        "deleted",
    ]
    search_fields = ["name", "slug", "description"]
    list_filter = ["is_active", "category", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["price", "stock", "is_active"]
    readonly_fields = [
        # "technical_specifications",
        "created_at",
        "updated_at",
        "deleted",
        "average_rating",
    ]
    fields = [
        "is_active",
        "name",
        "slug",
        "category",
        "price",
        "price_tag",
        "stock",
        "description",
        "technical_specifications",
        "image",
        "average_rating",
        "created_at",
        "updated_at",
        "deleted",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .annotate(
                _avg_rating=Avg("reviews__rating"),
                _review_count=Count("reviews"),
            )
        )

    @admin.display(description="Avg rating", ordering="_avg_rating")
    def avg_rating(self, obj: Product) -> str:
        avg = getattr(obj, "_avg_rating", None)
        count = getattr(obj, "_review_count", 0)
        if avg is None:
            return "No reviews"
        return f"{avg:.1f} ({count})"
