from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.db.models import Avg
from django.http import HttpRequest

from .models import Product


class ProductService:
    request: HttpRequest
    user: AbstractUser | AnonymousUser | None

    def __init__(
        self, request: HttpRequest, user: AbstractUser | AnonymousUser | None = None
    ) -> None:
        self.request = request
        self.user = user or getattr(request, "user", None)

    def update_product_rating(self, product: Product) -> None:
        """Updates the average rating of the given product based on its reviews."""
        from apps.reviews.models import Review

        approved_reviews = product.reviews.filter(status=Review.Status.APPROVED)
        average_rating = approved_reviews.aggregate(average=Avg("rating"))["average"] or 0.0
        product.average_rating = average_rating
        product.save(update_fields=["average_rating"])
