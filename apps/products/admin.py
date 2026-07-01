from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpRequest
from unfold.contrib.filters.admin import RangeDateFilter

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = ["name", "slug", "parent", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["parent"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted"]
    # fields = ["name", "slug", "parent", "created_at", "updated_at", "deleted"]

    fieldsets = (
        (None, {"fields": ("name", "slug", "parent")}),
        (
            ("Dates"),
            {"classes": ["collapse"], "fields": ("created_at", "updated_at", "deleted")},
        ),
    )


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
        "avg_rating",
        # "average_rating",
        "created_at",
        "updated_at",
        # "deleted",
    ]
    search_fields = ["name", "slug", "description"]
    list_filter = [
        "is_active",
        "category",
        ("created_at", DateFieldListFilter),
        ("created_at", RangeDateFilter),
    ]
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
                _review_count=Count("reviews"),
            )
        )

    @admin.display(description="Avg rating", ordering="average_rating")
    def avg_rating(self, obj: Product) -> str:
        avg = getattr(obj, "average_rating", None)
        count = getattr(obj, "_review_count", 0)
        if avg is None:
            return "No reviews"
        return f"{avg:.1f} ({count})"

    # Custom actions to mark users as active or inactive
    actions = ["mark_as_active", "mark_as_inactive"]

    @admin.action(description="Mark selected products as Active")
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} products successfully marked as Active.")

    @admin.action(description="Mark selected products as Inactive")
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} products successfully marked as Inactive.")
