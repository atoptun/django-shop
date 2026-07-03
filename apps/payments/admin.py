from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin

from apps.common.admin import BaseSafeDeleteUnfoldAdmin
from apps.payments.models import Payment, PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Payment)
class PaymentAdmin(BaseSafeDeleteUnfoldAdmin):
    list_display = ["id", "order", "payment_method", "transaction_id", "status", "created_at"]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["transaction_id", "order__id"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["mark_payment_completed"]

    @admin.action(description="Confirm payment status as Completed")
    def mark_payment_completed(self, request: HttpRequest, queryset: QuerySet[Payment]) -> None:
        updated_count = 0
        for payment in queryset:
            payment.status = Payment.Status.COMPLETED
            payment.save()
            # Also update order status
            order = payment.order
            # In Django, Order.Status is defined in models.TextChoices
            from apps.orders.models import Order

            order.status = Order.Status.PAID
            order.save()
            updated_count += 1
        self.message_user(request, f"Successfully confirmed {updated_count} payments.")
