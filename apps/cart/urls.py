from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.CartView.as_view(), name="cart_detail"),
    path("add/<slug:product_slug>/", views.AddToCartView.as_view(), name="add_to_cart"),
    path("update/<slug:product_slug>/", views.UpdateCartView.as_view(), name="update_cart"),
    path(
        "remove/<slug:product_slug>/",
        views.RemoveFromCartView.as_view(),
        name="remove_from_cart",
    ),
]
