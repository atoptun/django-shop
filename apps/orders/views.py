from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.products.models import Product

from .services import CartService


class CartView(TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_service = CartService(self.request)
        context["cart_items"] = cart_service.get_items()
        context["cart_total"] = cart_service.get_total_price()
        return context


class AddToCartView(View):
    def post(self, request, product_id, *args, **kwargs):
        cart_service = CartService(request)
        quantity = int(request.POST.get("quantity", 1))

        new_qty = cart_service.add(product_id, quantity)
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
    def post(self, request, product_id, *args, **kwargs):
        cart_service = CartService(request)
        action = request.POST.get("action")

        if action not in ["increase", "decrease", "remove"]:
            from django.http import HttpResponseBadRequest

            return HttpResponseBadRequest("Invalid or missing action")

        if action == "increase":
            current_qty = cart_service.get_product_quantity(product_id)
            new_qty = cart_service.update(product_id, current_qty + 1)
        elif action == "decrease":
            current_qty = cart_service.get_product_quantity(product_id)
            new_qty = cart_service.update(product_id, current_qty - 1)
        elif action == "remove":
            cart_service.remove(product_id)
            new_qty = 0

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
    def post(self, request, product_id, *args, **kwargs):
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


class CheckoutView(LoginRequiredMixin, TemplateView):
    template_name = "orders/checkout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = getattr(self.request.user, "profile", None)
        return context
