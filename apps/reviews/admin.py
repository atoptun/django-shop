from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Review


@admin.register(Review)
class ReviewAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = [
        "pk",
        "product",
        "user",
        "rating",
        "status",
        "comment",
        "created_at",
    ]
    list_per_page = 50
    list_max_show_all = 200
    search_fields = ["product__name", "user__username", "comment"]
    list_filter = ["status", "rating", "created_at"]
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "product",
        "user",
        "rating",
        "status",
        "comment",
        "created_at",
    ]
    actions = ["approve_reviews", "reject_reviews"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Prefetch related product and user fields for review queries."""
        return super().get_queryset(request).select_related("product", "user")

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Approve selected reviews and update corresponding product ratings."""
        queryset.update(status=Review.Status.APPROVED)
        product_ids = queryset.values_list("product_id", flat=True).distinct()
        from apps.products.models import Product
        from apps.products.services import ProductService

        product_service = ProductService(request)
        for p_id in product_ids:
            product = Product.objects.get(id=p_id)
            product_service.update_product_rating(product)

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Reject selected reviews and update corresponding product ratings."""
        queryset.update(status=Review.Status.REJECTED)
        product_ids = queryset.values_list("product_id", flat=True).distinct()
        from apps.products.models import Product
        from apps.products.services import ProductService

        product_service = ProductService(request)
        for p_id in product_ids:
            product = Product.objects.get(id=p_id)
            product_service.update_product_rating(product)

    def save_model(self, request: HttpRequest, obj: Review, form: Any, change: bool) -> None:
        """Saves a review instance and updates product average ratings on status changes."""
        status_changed = True
        if change:
            db_obj = Review.objects.get(pk=obj.pk)
            status_changed = db_obj.status != obj.status

        super().save_model(request, obj, form, change)

        if status_changed:
            from apps.products.services import ProductService

            product_service = ProductService(request)
            product_service.update_product_rating(obj.product)
