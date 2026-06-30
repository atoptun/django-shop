# Register your models here.
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Review


@admin.register(Review)
class ReviewAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = [
        "product",
        "user",
        "rating",
        "comment",
        "created_at",
        "updated_at",
        "deleted",
    ]
    search_fields = ["product__name", "user__username", "comment"]
    list_filter = ["rating", "created_at"]
    readonly_fields = ["created_at", "updated_at", "deleted"]
    fields = [
        "product",
        "user",
        "rating",
        "comment",
        "created_at",
        "updated_at",
        "deleted",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("product", "user")
