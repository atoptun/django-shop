from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list_home"),
    path(
        "products/",
        views.ProductListView.as_view(),
        name="list",
    ),
    path(
        "products/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="detail",
    ),
]
