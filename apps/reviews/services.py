from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.http import HttpRequest
from rest_framework.request import Request as DRFRequest

from apps.orders.models import Order
from apps.products.models import Product
from apps.reviews.models import Review


class ReviewService:
    request: HttpRequest | DRFRequest | None
    user: AbstractUser | AnonymousUser | None

    def __init__(
        self,
        request: HttpRequest | DRFRequest | None,
        user: AbstractUser | AnonymousUser | None = None,
    ) -> None:
        self.request = request
        self.user = user or getattr(request, "user", None)

    def get_reviews_for_product(self, product: Product) -> list[Review]:
        """
        Returns a list of reviews for the given product,
        ordered by creation date (most recent first).
        """
        reviews = list(
            Review.objects.filter(product=product, status=Review.Status.APPROVED)
            .select_related("user")
            .order_by("-created_at")
            .all()
        )
        return reviews

    def can_user_review_product(self, product: Product) -> bool:
        """Returns True if the user can review the given product, False otherwise."""
        if not (self.user and self.user.is_authenticated):
            return False

        can_review = Order.objects.filter(
            user=self.user,
            items__product=product,
            status__in=[Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED],
        ).exists()

        return can_review

    def user_already_reviewed_product(self, product: Product) -> bool:
        """Returns True if the user has already reviewed the given product, False otherwise."""
        if not (self.user and self.user.is_authenticated):
            return False

        already_reviewed = Review.objects.filter(product=product, user=self.user).exists()
        return already_reviewed

    def create_review(self, product: Product, rating: int, comment: str) -> Review:
        """Creates a pending review for the product by the authenticated user."""
        if not (self.user and self.user.is_authenticated):
            raise ValueError("Authenticated user required to write a review.")

        review = Review.objects.create(
            product=product,
            user=self.user,
            rating=rating,
            comment=comment,
            status=Review.Status.PENDING,
        )
        return review
