from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/add/<int:product_id>/", views.AddToCartView.as_view(), name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.UpdateCartView.as_view(), name="update_cart"),
    path(
        "cart/remove/<int:product_id>/", views.RemoveFromCartView.as_view(), name="remove_from_cart"
    ),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
]
