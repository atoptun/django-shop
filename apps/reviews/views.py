from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView

from apps.products.models import Product

from .forms import ReviewForm
from .services import ReviewService


class AddReviewView(LoginRequiredMixin, CreateView):
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=kwargs["slug"])

        service = ReviewService(request)

        can_review = service.can_user_review_product(product)
        already_reviewed = service.user_already_reviewed_product(product)

        if not can_review:
            messages.error(request, "You can only review products you have purchased.")
            return redirect(product.get_absolute_url())

        if already_reviewed:
            messages.info(request, "You have already reviewed this product.")
            return redirect(product.get_absolute_url())

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review added!")

        return redirect(product.get_absolute_url())
