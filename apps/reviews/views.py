from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView

from .forms import ReviewForm
from .models import Review


class AddReviewView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = "reviews/add_review.html"
