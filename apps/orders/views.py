from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View

from apps.cart.services import CartService
from apps.payments.models import PaymentMethod

from .services import OrderService


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect("cart:cart_detail")

        from apps.orders.forms import CheckoutForm

        form = CheckoutForm(user=request.user)
        return self._render_checkout_page(request, form, cart_service)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect("cart:cart_detail")

        from apps.orders.forms import CheckoutForm
        from apps.payments.forms import (
            BankTransferPaymentForm,
            CardPaymentForm,
            CashOnDeliveryForm,
            PayPalPaymentForm,
            get_payment_form_class,
        )
        from apps.payments.services import PaymentService

        form = CheckoutForm(request.POST, user=request.user)
        if not form.is_valid():
            return self._render_checkout_page(request, form, cart_service)

        cleaned_data = form.cleaned_data
        shipping_address = self._get_shipping_address(request, cleaned_data)
        user = request.user
        assert isinstance(user, AbstractUser), "User must be AbstractUser"
        payment_method = cleaned_data["payment_method"]

        # Validate the corresponding payment method inputs
        form_class = get_payment_form_class(payment_method.code)
        payment_form = form_class(request.POST)

        if not payment_form.is_valid():
            messages.error(request, "Invalid payment details provided.")
            forms_map = {
                "debit": CardPaymentForm(),
                "wallet": PayPalPaymentForm(),
                "bank": BankTransferPaymentForm(),
                "cod": CashOnDeliveryForm(),
            }
            forms_map[payment_method.code.lower()] = payment_form
            return self._render_checkout_page(request, form, cart_service, forms_map)

        try:
            # 1. Create order
            order = OrderService.create_order(cart_service, user, shipping_address, payment_method)
        except ValueError as e:
            messages.error(request, str(e))
            return self._render_checkout_page(request, form, cart_service)

        # 2. Process payment immediately
        payment_data = payment_form.cleaned_data
        result = PaymentService.process_order_payment(order, payment_method, payment_data)

        if result["success"]:
            from apps.payments.models import Payment

            if result["status"] == Payment.Status.COMPLETED:
                messages.success(request, "Order placed and payment was successful!")
            elif result["status"] == Payment.Status.PROCESSING:
                messages.info(
                    request,
                    "Order placed! Payment is being processed "
                    "(Bank Transfer). Waiting for verification.",
                )
            elif result["status"] == Payment.Status.PENDING:
                messages.success(
                    request,
                    "Order placed successfully via Cash On Delivery! Pay on arrival.",
                )
            return redirect("accounts:order_history")
        else:
            messages.warning(
                request,
                f"Order created, but payment failed: {result['error']}. "
                "Please retry your payment below.",
            )
            return redirect("payments:pay", order_uuid=order.uuid)

    def _render_checkout_page(
        self,
        request: HttpRequest,
        form: Any,
        cart_service: CartService,
        forms_map: dict | None = None,
    ) -> HttpResponse:
        """Renders the checkout page with the provided form and cart details."""
        if not forms_map:
            from apps.payments.forms import (
                BankTransferPaymentForm,
                CardPaymentForm,
                CashOnDeliveryForm,
                PayPalPaymentForm,
            )

            forms_map = {
                "debit": CardPaymentForm(),
                "wallet": PayPalPaymentForm(),
                "bank": BankTransferPaymentForm(),
                "cod": CashOnDeliveryForm(),
            }

        payment_methods = PaymentMethod.objects.filter(is_active=True)
        selected_method = (
            form.payment_method.value
            if hasattr(form, "payment_method")
            else payment_methods.first()
        )

        context = {
            "form": form,
            "cart_items": cart_service.get_items(),
            "cart_total": cart_service.get_total_price(),
            "profile": getattr(request.user, "profile", None),
            "payment_methods": payment_methods,
            "selected_method": selected_method,
            "forms": forms_map,
        }
        from django.shortcuts import render

        return render(request, "orders/checkout.html", context)

    def _get_shipping_address(self, request: HttpRequest, cleaned_data: dict[str, Any]) -> str:
        """Determines the shipping address based on the user's selection or input."""
        address_choice: str = cleaned_data.get("address_choice", "")
        if address_choice and address_choice != "new":
            from apps.accounts.models import Address

            addr = Address.objects.get(id=int(address_choice), user=request.user)
            return (
                f"Recipient: {addr.recipient_name}\n"
                f"Phone: {addr.phone}\n"
                f"City: {addr.city}\n"
                f"Address: {addr.address_line}"
            )
        return (
            f"Recipient: {cleaned_data['full_name']}\n"
            f"Phone: {cleaned_data['phone']}\n"
            f"City: {cleaned_data['city']}\n"
            f"Address: {cleaned_data['address']}"
        )
