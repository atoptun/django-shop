import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.orders.factories import OrderFactory, OrderItemFactory
from apps.orders.models import Order
from apps.products.factories import ProductFactory
from apps.reviews.factories import ReviewFactory
from apps.reviews.models import Review
from apps.reviews.services import ReviewService

pytestmark = pytest.mark.django_db


# --- Model Tests ---


def test_review_creation():
    user = UserFactory(username="reviewer")
    product = ProductFactory(name="Laptop")
    review = ReviewFactory(user=user, product=product, rating=4, comment="Great laptop!")

    assert review.user == user
    assert review.product == product
    assert review.rating == 4
    assert review.comment == "Great laptop!"
    assert str(review) == f"Review by {user.username} for Laptop"


def test_review_rating_validation():
    product = ProductFactory()
    user = UserFactory()

    # Invalid low rating
    review_low = Review(product=product, user=user, rating=0, comment="Bad")
    with pytest.raises(ValidationError):
        review_low.full_clean()

    # Invalid high rating
    review_high = Review(product=product, user=user, rating=6, comment="Superb")
    with pytest.raises(ValidationError):
        review_high.full_clean()

    # Valid rating
    review_valid = Review(product=product, user=user, rating=5, comment="Nice")
    # should not raise
    review_valid.full_clean()


# --- Service Tests ---


def test_get_reviews_for_product():
    product = ProductFactory()
    r1 = ReviewFactory(product=product)
    r2 = ReviewFactory(product=product)

    service = ReviewService(request=None)
    reviews = service.get_reviews_for_product(product)

    assert len(reviews) == 2
    # Ordered by most recent first
    assert reviews[0] == r2
    assert reviews[1] == r1


def test_can_user_review_product():
    user = UserFactory()
    product = ProductFactory()

    # Anonymous user cannot review
    service_anon = ReviewService(request=None, user=None)
    assert service_anon.can_user_review_product(product) is False

    # User with no order cannot review
    service_user = ReviewService(request=None, user=user)
    assert service_user.can_user_review_product(product) is False

    # User with pending order cannot review
    order_pending = OrderFactory(user=user, status=Order.Status.PENDING)
    OrderItemFactory(order=order_pending, product=product)
    assert service_user.can_user_review_product(product) is False

    # User with paid order can review
    order_paid = OrderFactory(user=user, status=Order.Status.PAID)
    OrderItemFactory(order=order_paid, product=product)
    assert service_user.can_user_review_product(product) is True


def test_user_already_reviewed_product():
    user = UserFactory()
    product = ProductFactory()
    service = ReviewService(request=None, user=user)

    # Not reviewed yet
    assert service.user_already_reviewed_product(product) is False

    # Reviewed
    ReviewFactory(user=user, product=product)
    assert service.user_already_reviewed_product(product) is True


# --- View Tests ---


def test_add_review_unauthenticated(client):
    product = ProductFactory()
    url = reverse("reviews:add_review", kwargs={"slug": product.slug})
    response = client.post(url, {"rating": 5, "comment": "Excellent"})

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_add_review_no_purchase(client):
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory()
    url = reverse("reviews:add_review", kwargs={"slug": product.slug})
    response = client.post(url, {"rating": 5, "comment": "Excellent"})

    assert response.status_code == 302
    assert response.url == product.get_absolute_url()

    # Check error message
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "You can only review products you have purchased" in str(messages[0])


def test_add_review_success(client):
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(stock=10)
    # Order the product
    order = OrderFactory(user=user, status=Order.Status.PAID)
    OrderItemFactory(order=order, product=product)

    url = reverse("reviews:add_review", kwargs={"slug": product.slug})
    response = client.post(url, {"rating": 5, "comment": "Amazing!"})

    assert response.status_code == 302
    assert response.url == product.get_absolute_url()

    # Check review was created
    assert Review.objects.filter(user=user, product=product, rating=5).exists()

    # Check messages
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Review added!" in str(messages[0])


def test_add_review_duplicate(client):
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory()
    order = OrderFactory(user=user, status=Order.Status.PAID)
    OrderItemFactory(order=order, product=product)

    # Already has a review
    ReviewFactory(user=user, product=product)

    url = reverse("reviews:add_review", kwargs={"slug": product.slug})
    response = client.post(url, {"rating": 4, "comment": "Another one"})

    assert response.status_code == 302
    assert response.url == product.get_absolute_url()

    # No duplicate review
    assert Review.objects.filter(user=user, product=product).count() == 1

    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "You have already reviewed this product" in str(messages[0])
