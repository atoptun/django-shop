from typing import Any

from django.contrib import admin
from django.db import transaction
from django.forms import BaseInlineFormSet, ValidationError
from django.http import HttpRequest
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.common.admin import BaseSafeDeleteUnfoldAdmin

from .models import Order, OrderItem, Payment, PaymentMethod
from .services import OrderService


class OrderItemInlineFormSet(BaseInlineFormSet):
    def clean(self) -> None:
        """Validates stock availability and duplicate products in order items."""
        super().clean()

        product_ids: list[int] = []

        for form in self.forms:
            if not form.is_valid() or (self.can_delete and form.cleaned_data.get("DELETE")):
                continue

            cleaned_data = form.cleaned_data
            product = cleaned_data.get("product")
            qty = cleaned_data.get("quantity")

            if not product or qty is None:
                continue

            if product.id in product_ids:
                raise ValidationError(f"Duplicate product '{product.name}' in order items.")

            product_ids.append(product.id)

            if qty <= 0:
                raise ValidationError("Quantity must be greater than zero.")

            self._check_form_stock(form, product, qty)

    def _check_form_stock(self, form: Any, product: Any, qty: int) -> None:
        """Helper method to validate stock for a single inline form item."""
        if form.instance.pk:
            try:
                db_instance = OrderItem.objects.get(pk=form.instance.pk)
            except OrderItem.DoesNotExist as err:
                if product.stock < qty:
                    raise ValidationError(
                        f"Insufficient stock for {product.name}. Only {product.stock} available."
                    ) from err
                return

            if db_instance.product != product:
                if product.stock < qty:
                    raise ValidationError(
                        f"Insufficient stock for {product.name}. Only {product.stock} available."
                    )
            else:
                diff = qty - db_instance.quantity
                if diff > 0 and product.stock < diff:
                    raise ValidationError(
                        f"Insufficient stock for {product.name}. Only {product.stock} available."
                    )
        else:
            if product.stock < qty:
                raise ValidationError(
                    f"Insufficient stock for {product.name}. Only {product.stock} available."
                )

    def save(self, commit: bool = True) -> list[Any]:
        """Saves new, changed, and deleted inline order items with stock adjustments."""
        with transaction.atomic():
            # 1. Return stock of deleted inlines
            for form in self.deleted_forms:
                if form.instance.pk:
                    OrderService.adjust_stock(form.instance.product, -form.instance.quantity)
                    form.instance.delete()

            # 2. Process new/changed inlines
            saved_instances: list[Any] = []
            super().save(commit=False)
            for form in self.forms:
                is_deleted = self.can_delete and form.cleaned_data.get("DELETE")
                if not form.is_valid() or is_deleted or not form.has_changed():
                    continue

                instance = form.instance
                if instance.pk:
                    db_instance = OrderItem.objects.get(pk=instance.pk)
                    if db_instance.product != instance.product:
                        # Product changed: return old stock, reserve new stock
                        OrderService.adjust_stock(db_instance.product, -db_instance.quantity)
                        OrderService.adjust_stock(instance.product, instance.quantity)
                        instance.price = instance.product.price
                        instance.save()
                    else:
                        # Quantity changed
                        new_qty = form.cleaned_data.get("quantity")
                        OrderService.update_order_item(instance, db_instance.quantity, new_qty)
                else:
                    # New item inline added
                    qty = form.cleaned_data.get("quantity")
                    OrderService.adjust_stock(instance.product, qty)
                    instance.price = instance.product.price
                    instance.save()

                saved_instances.append(instance)

            # 3. Update parent order total
            if self.instance and hasattr(self.instance, "pk"):
                OrderService.recalculate_order_total(self.instance)

        return saved_instances


# Inline order items inside the Order details page
class OrderItemInline(TabularInline):
    model = OrderItem
    formset = OrderItemInlineFormSet
    extra = 0
    tab = True
    can_add = True
    can_delete = True
    raw_id_fields = ["product"]

    def get_readonly_fields(
        self, request: HttpRequest, obj: Order | None = None
    ) -> list[str] | tuple[str, ...]:
        """Make all inline fields read-only if the parent order status is not PENDING."""
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.status != Order.Status.PENDING:
            return list(set(list(readonly_fields) + ["product", "quantity", "price"]))
        return readonly_fields

    def has_add_permission(self, request: HttpRequest, obj: Order | None = None) -> bool:
        """Prevent adding new inline items if the parent order status is not PENDING."""
        if obj and obj.status != Order.Status.PENDING:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Order | None = None) -> bool:
        """Prevent deleting existing inline items if the parent order status is not PENDING."""
        if obj and obj.status != Order.Status.PENDING:
            return False
        return super().has_delete_permission(request, obj)


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
    readonly_fields = ["user", "total_price", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {"fields": ["user", "status", "total_price", "shipping_address"]}),
        ("Dates", {"classes": ("collapse",), "fields": ["created_at", "updated_at"]}),
    )

    def get_readonly_fields(
        self, request: HttpRequest, obj: Order | None = None
    ) -> list[str] | tuple[str, ...]:
        """Make all fields read-only for orders in final status."""
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.status in [
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
            Order.Status.CANCELLED,
        ]:
            # Make all fields read-only for orders in final status
            return list(set(list(readonly_fields) + [field.name for field in obj._meta.fields]))
        return readonly_fields

    def save_model(self, request: HttpRequest, obj: Order, form: Any, change: bool) -> None:
        """Handles status changes and delegates order cancellation to the Service layer."""
        if change:
            db_obj = Order.objects.get(pk=obj.pk)
            if db_obj.status != obj.status and obj.status == Order.Status.CANCELLED:
                # Cancel order using the service, which also saves it to DB
                OrderService.cancel_order(obj)
                return

        super().save_model(request, obj, form, change)


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
