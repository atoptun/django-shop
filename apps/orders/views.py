from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.products.models import Product

from .services import CartService


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
            from django.contrib import messages

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
            from django.contrib import messages

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
            from django.contrib import messages

            messages.warning(request, "Your cart is empty.")
            return redirect("orders:cart")

        from apps.orders.forms import CheckoutForm

        form = CheckoutForm(user=request.user)
        context = {
            "form": form,
            "cart_items": cart_service.get_items(),
            "cart_total": cart_service.get_total_price(),
            "profile": getattr(request.user, "profile", None),
        }
        from django.shortcuts import render

        return render(request, "orders/checkout.html", context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cart_service = CartService(request)
        if cart_service.get_total_items() == 0:
            from django.contrib import messages

            messages.warning(request, "Your cart is empty.")
            return redirect("orders:cart")

        from apps.orders.forms import CheckoutForm

        form = CheckoutForm(request.POST, user=request.user)
        if not form.is_valid():
            context = {
                "form": form,
                "cart_items": cart_service.get_items(),
                "cart_total": cart_service.get_total_price(),
                "profile": getattr(request.user, "profile", None),
            }
            from django.shortcuts import render

            return render(request, "orders/checkout.html", context)

        cleaned_data = form.cleaned_data
        address_choice: str = cleaned_data.get("address_choice", "")
        payment_method = cleaned_data["payment_method"]

        if address_choice and address_choice != "new":
            from apps.accounts.models import Address

            addr = Address.objects.get(id=int(address_choice), user=request.user)
            shipping_address = (
                f"Recipient: {addr.recipient_name}\n"
                f"Phone: {addr.phone}\n"
                f"City: {addr.city}\n"
                f"Address: {addr.address_line}"
            )
        else:
            shipping_address = (
                f"Recipient: {cleaned_data['full_name']}\n"
                f"Phone: {cleaned_data['phone']}\n"
                f"City: {cleaned_data['city']}\n"
                f"Address: {cleaned_data['address']}"
            )

        from uuid import uuid4

        from django.contrib import messages
        from django.db import transaction

        from apps.orders.models import CartItem, Order, OrderItem, Payment

        try:
            with transaction.atomic():
                cart_items = cart_service.get_items()
                # 1. Concurrency safe stock reservation
                for item in cart_items:
                    product = Product.objects.select_for_update().get(id=item["product"].id)
                    if product.stock < item["quantity"]:
                        raise ValueError(
                            f"Not enough stock for {product.name}. "
                            f"Available: {product.stock}, in cart: {item['quantity']}."
                        )
                    product.stock -= item["quantity"]
                    product.save()

                # 2. Order creation
                order = Order.objects.create(
                    user=request.user,
                    status=Order.Status.PENDING,
                    total_price=cart_service.get_total_price(),
                    shipping_address=shipping_address,
                )

                # 3. Order Items creation
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item["product"],
                        quantity=item["quantity"],
                        price=item["product"].price,
                    )

                # 4. Payment record creation
                Payment.objects.create(
                    order=order, payment_method=payment_method, transaction_id=f"PAY-{uuid4()}"
                )

                # 5. Clear Cart
                CartItem.objects.filter(cart=cart_service.cart).delete()

        except ValueError as e:
            messages.error(request, str(e))
            context = {
                "form": form,
                "cart_items": cart_service.get_items(),
                "cart_total": cart_service.get_total_price(),
                "profile": getattr(request.user, "profile", None),
            }
            from django.shortcuts import render

            return render(request, "orders/checkout.html", context)

        # 6. Email notifications
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail

        try:
            send_mail(
                subject=f"Order Confirmation - Order #{order.pk}",
                message=(
                    f"Hello {request.user.username or 'Customer'},\n\n"
                    f"Thank you for your order!\n\n"
                    f"Order Details:\n"
                    f"Order ID: #{order.pk}\n"
                    f"Total: ${order.total_price}\n"
                    f"Shipping Address:\n{order.shipping_address}\n\n"
                    f"We will process your order soon."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=True,
            )

            User = get_user_model()
            admin_emails = list(User.objects.filter(is_staff=True).values_list("email", flat=True))
            if not admin_emails:
                admin_emails = ["admin@example.com"]

            send_mail(
                subject=f"New Order Placed - Order #{order.pk}",
                message=(
                    f"A new order #{order.pk} has been placed by user: {request.user.username}.\n"
                    f"Total: ${order.total_price}\n"
                    f"Shipping Address:\n{order.shipping_address}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )
        except Exception as mail_err:
            print(f"Failed to send checkout email notifications: {mail_err}")

        messages.success(request, f"Order #{order.pk} placed successfully!")
        return redirect("accounts:order_history")
