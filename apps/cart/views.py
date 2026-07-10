from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.cart.services import CartService


class CartView(TemplateView):
    template_name = "cart/cart.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        cart_service = CartService(self.request)
        context["cart_items"] = cart_service.get_items()
        context["cart_total"] = cart_service.get_total_price()
        return context


class AddToCartView(View):
    def post(
        self, request: HttpRequest, product_slug: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1

        try:
            new_qty = cart_service.add(product_slug, quantity)
        except ValueError as e:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)

            messages.error(request, str(e))
            return redirect("cart:cart_detail")

        total_items = cart_service.get_total_items()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "product_quantity": new_qty,
                    "cart_total_items": total_items,
                }
            )
        return redirect("cart:cart_detail")


class UpdateCartView(View):
    def post(
        self, request: HttpRequest, product_slug: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        action = request.POST.get("action", "")

        if action not in ["increase", "decrease", "remove"]:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Invalid action"}, status=400)
            messages.error(request, "Invalid cart action.")
            return redirect("cart:cart_detail")

        try:
            new_qty = 0
            if action == "increase":
                current_qty = cart_service.get_product_quantity(product_slug)
                new_qty = cart_service.update(product_slug, current_qty + 1)
            elif action == "decrease":
                current_qty = cart_service.get_product_quantity(product_slug)
                new_qty = cart_service.update(product_slug, current_qty - 1)
            elif action == "remove":
                cart_service.remove(product_slug)
                new_qty = 0
        except ValueError as e:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)

            messages.error(request, str(e))
            return redirect("cart:cart_detail")

        items = cart_service.get_items()
        items_by_slug = {i["product"].slug: i for i in items}
        total_items = sum(i["quantity"] for i in items)
        total_price = sum((i["subtotal"] for i in items), Decimal(0))
        subtotal = items_by_slug.get(product_slug, {}).get("subtotal", Decimal(0))

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
        return redirect("cart:cart_detail")


class RemoveFromCartView(View):
    def post(
        self, request: HttpRequest, product_slug: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        cart_service = CartService(request)
        cart_service.remove(product_slug)
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
        return redirect("cart:cart_detail")
