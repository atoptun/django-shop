from django.urls import path
from django.views.generic import TemplateView

app_name = "products"

urlpatterns = [
    path("", TemplateView.as_view(template_name="products/home.html"), name="list_home"),
    path(
        "products/",
        TemplateView.as_view(template_name="products/product_list.html"),
        name="list",
    ),
    path(
        "products/<int:pk>/",
        TemplateView.as_view(template_name="products/product_detail.html"),
        name="detail",
    ),
]
