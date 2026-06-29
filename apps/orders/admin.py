from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Order, OrderItem, Payment, PaymentMethod


# Inline order items inside the Order details page
class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    tab = True
    raw_id_fields = ["product"]


# Inline payment record inside the Order details page
class PaymentInline(StackedInline):
    model = Payment
    extra = 0
    tab = True
    raw_id_fields = ["payment_method"]


@admin.register(Order)
class OrderAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = ["id", "user", "status", "total_price", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "user__email", "shipping_address"]
    inlines = [OrderItemInline, PaymentInline]
    date_hierarchy = "created_at"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Payment)
class PaymentAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = ["id", "order", "payment_method", "transaction_id", "created_at"]
    list_filter = ["payment_method", "created_at"]
    search_fields = ["transaction_id", "order__id"]
