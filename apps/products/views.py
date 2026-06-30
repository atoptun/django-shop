from typing import Any

from django.db import models
from django.views.generic import DetailView, ListView

from .models import Category, Product


class ProductListView(ListView):
    model: type[Product] = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        queryset = self.model.objects.filter(is_active=True)

        search_query = self.request.GET.get("search", "")
        categories = self.request.GET.getlist("category")

        if search_query:
            queryset = queryset.filter(
                models.Q(name__icontains=search_query)
                | models.Q(description__icontains=search_query)
            )

        if categories:
            queryset = queryset.filter(category__slug__in=categories).distinct()
            queryset = queryset.filter(
                models.Q(category__slug__in=categories)
                | models.Q(category__parent__slug__in=categories)
            )

        allowed_sorts = {
            "new": ["-created_at"],
            "price_asc": [
                "price",
            ],
            "price_desc": [
                "-price",
            ],
            "rating": ["-average_rating", "-created_at"],
        }

        sort_by = self.request.GET.get("sort", "new")
        if sort_by not in allowed_sorts:
            sort_by = "new"

        queryset = queryset.order_by(*allowed_sorts[sort_by])

        return queryset

    def get_context_data(self, *, object_list=None, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(object_list=object_list, **kwargs)

        context["sort_by"] = self.request.GET.get("sort", "new")
        context["selected_categories"] = self.request.GET.getlist("category")
        context["search_query"] = self.request.GET.get("search", "")
        categories = Category.objects.all().order_by("name")
        context["categories"] = categories

        return context


class ProductDetailView(DetailView):
    model: type[Product] = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return self.model.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        from apps.orders.services import CartService
        from apps.reviews.services import ReviewService

        cart_service = CartService(self.request)
        context["in_cart_quantity"] = cart_service.get_product_quantity(self.object.id)

        review_service = ReviewService(self.request)
        context["reviews"] = review_service.get_reviews_for_product(product)
        can_review = review_service.can_user_review_product(product)
        already_reviewed = review_service.user_already_reviewed_product(product)
        review_form = None

        if can_review and not already_reviewed:
            from apps.reviews.forms import ReviewForm

            review_form = ReviewForm()
            context["review_form"] = review_form

        context["can_review"] = can_review
        context["already_reviewed"] = already_reviewed
        context["review_form"] = review_form

        return context
