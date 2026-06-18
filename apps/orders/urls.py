from django.urls import path
from django.views.generic import TemplateView

app_name = "orders"

urlpatterns = [
    path("cart/", TemplateView.as_view(template_name="orders/cart.html"), name="cart"),
    path("cart/add/", TemplateView.as_view(template_name="orders/cart.html"), name="add_to_cart"),
    path(
        "cart/update/", TemplateView.as_view(template_name="orders/cart.html"), name="update_cart"
    ),
    path(
        "cart/remove/",
        TemplateView.as_view(template_name="orders/cart.html"),
        name="remove_from_cart",
    ),
    path("checkout/", TemplateView.as_view(template_name="orders/checkout.html"), name="checkout"),

    # path("cart/add/", AddToCartView.as_view(), name="add_to_cart"),
    # path("cart/update/", UpdateCartView.as_view(), name="update_cart"),
    # path("cart/remove/", RemoveFromCartView.as_view(), name="remove_from_cart"),
    # path("checkout/", CheckoutView.as_view(), name="checkout"),
]
