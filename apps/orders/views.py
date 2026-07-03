from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.payments.models import PaymentMethod
from apps.products.models import Product

from .services import CartService, OrderService


class CartView(TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        cart_service = CartService(self.request)
        context["cart_items"] = cart_service.get_items()
        context["cart_total"] = cart_service.get_total_price()
        return context


class AddToCartView(View):
    def post(
        self, request: HttpRequest, product_id: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        quantity = int(request.POST.get("quantity", 1))

        try:
            new_qty = cart_service.add(product_id, quantity)
        except ValueError as e:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)

            messages.error(request, str(e))
            return redirect("orders:cart")

        total_items = cart_service.get_total_items()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "product_quantity": new_qty,
                    "cart_total_items": total_items,
                }
            )
        return redirect("orders:cart")


class UpdateCartView(View):
    def post(
        self, request: HttpRequest, product_id: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        action = request.POST.get("action", "")

        if action not in ["increase", "decrease", "remove"]:
            from django.http import HttpResponseBadRequest

            return HttpResponseBadRequest("Invalid or missing action")

        try:
            new_qty = 0
            if action == "increase":
                current_qty = cart_service.get_product_quantity(product_id)
                new_qty = cart_service.update(product_id, current_qty + 1)
            elif action == "decrease":
                current_qty = cart_service.get_product_quantity(product_id)
                new_qty = cart_service.update(product_id, current_qty - 1)
            elif action == "remove":
                cart_service.remove(product_id)
                new_qty = 0
        except ValueError as e:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)

            messages.error(request, str(e))
            return redirect("orders:cart")

        total_items = cart_service.get_total_items()
        total_price = cart_service.get_total_price()

        try:
            product = Product.objects.get(id=product_id)
            subtotal = product.price * new_qty
        except Product.DoesNotExist:
            subtotal = 0

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "product_quantity": new_qty,
                    "cart_total_items": total_items,
                    "item_subtotal": f"${subtotal:.2f}",
                    "cart_total_price": f"${total_price:.2f}",
                }
            )
        return redirect("orders:cart")


class RemoveFromCartView(View):
    def post(
        self, request: HttpRequest, product_id: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        cart_service.remove(product_id)
        total_items = cart_service.get_total_items()
        total_price = cart_service.get_total_price()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "product_quantity": 0,
                    "cart_total_items": total_items,
                    "cart_total_price": f"${total_price:.2f}",
                }
            )
        return redirect("orders:cart")


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect("orders:cart")

        from apps.orders.forms import CheckoutForm

        form = CheckoutForm(user=request.user)
        return self._render_checkout_page(request, form, cart_service)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect("orders:cart")

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
        assert isinstance(user, AbstractUser), "User must be"
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
