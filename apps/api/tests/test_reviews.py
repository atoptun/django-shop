from datetime import timedelta
from typing import cast

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.api.tests import AuthClient
from apps.orders.factories import OrderFactory, OrderItemFactory
from apps.orders.models import Order
from apps.products.factories import ProductFactory
from apps.reviews.factories import ReviewFactory
from apps.reviews.models import Review

# =============================================================================
# GET /api/products/<slug>/reviews/
# =============================================================================


@pytest.mark.django_db
def test_get_reviews_success(api_client: APIClient) -> None:
    product = ProductFactory(slug="beer-lager")

    # Set explicit created_at to avoid same-second nondeterminism
    now = timezone.now()
    r1 = ReviewFactory(
        product=product,
        rating=5,
        comment="Amazing!",
        status=Review.Status.APPROVED,
        created_at=now - timedelta(minutes=10),
    )
    r2 = ReviewFactory(
        product=product,
        rating=4,
        comment="Good.",
        status=Review.Status.APPROVED,
        created_at=now - timedelta(minutes=5),
    )
    ReviewFactory(
        product=product,
        rating=1,
        comment="Bad.",
        status=Review.Status.PENDING,
        created_at=now,
    )

    url = reverse("api:product-reviews-list", kwargs={"slug": product.slug})
    res = cast(Response, api_client.get(url))

    assert res.status_code == status.HTTP_200_OK
    res_data = cast(dict, res.data)
    results = res_data["results"]
    assert len(results) == 2

    # Verify sorting (most recent first)
    assert results[0]["comment"] == r2.comment
    assert results[1]["comment"] == r1.comment

    # Verify keys
    assert results[0]["rating"] == 4
    assert "created_at" in results[0]
    assert "id" in results[0]
    assert results[0]["user"]["username"] == r2.user.username


@pytest.mark.django_db
def test_get_reviews_empty_or_not_found(api_client: APIClient) -> None:
    # Non-existent product slug should return 404
    url = reverse("api:product-reviews-list", kwargs={"slug": "non-existent-slug"})
    res = cast(Response, api_client.get(url))
    assert res.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# GET /api/products/<slug>/reviews/can-review/
# =============================================================================


@pytest.mark.django_db
def test_can_review_status_unauthenticated(api_client: APIClient) -> None:
    url = reverse("api:product-reviews-can-review", kwargs={"slug": "lager"})
    res = cast(Response, api_client.get(url))
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_can_review_status_buyer_success(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    user = auth_client.user

    # Purchase the product
    order = OrderFactory(user=user, status=Order.Status.PAID)
    OrderItemFactory(order=order, product=product)

    url = reverse("api:product-reviews-can-review", kwargs={"slug": product.slug})
    res = cast(Response, auth_client.get(url))

    assert res.status_code == status.HTTP_200_OK
    res_data = cast(dict, res.data)
    assert res_data["can_review"] is True
    assert res_data["already_reviewed"] is False


@pytest.mark.django_db
def test_can_review_status_toggles_already_reviewed(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    user = auth_client.user

    order = OrderFactory(user=user, status=Order.Status.DELIVERED)
    OrderItemFactory(order=order, product=product)

    url_check = reverse("api:product-reviews-can-review", kwargs={"slug": product.slug})
    url_create = reverse("api:product-reviews-list", kwargs={"slug": product.slug})

    # 1. Initially not reviewed
    res_initial = cast(Response, auth_client.get(url_check))
    assert res_initial.status_code == status.HTTP_200_OK
    assert cast(dict, res_initial.data)["can_review"] is True
    assert cast(dict, res_initial.data)["already_reviewed"] is False

    # 2. Create review
    res_create = cast(
        Response, auth_client.post(url_create, {"rating": 5, "comment": "Okay"}, format="json")
    )
    assert res_create.status_code == status.HTTP_201_CREATED

    # 3. Verify flag flipped to True
    res_after = cast(Response, auth_client.get(url_check))
    assert res_after.status_code == status.HTTP_200_OK
    assert cast(dict, res_after.data)["can_review"] is True
    assert cast(dict, res_after.data)["already_reviewed"] is True


# =============================================================================
# POST /api/products/<slug>/reviews/
# =============================================================================


@pytest.mark.django_db
def test_create_review_unauthenticated(api_client: APIClient) -> None:
    url = reverse("api:product-reviews-list", kwargs={"slug": "lager"})
    data = {"rating": 5, "comment": "Good!"}
    res = cast(Response, api_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_create_review_not_purchased_fails(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    url = reverse("api:product-reviews-list", kwargs={"slug": product.slug})
    data = {"rating": 5, "comment": "I did not buy this."}

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_review_success(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    user = auth_client.user

    # Purchase the product
    order = OrderFactory(user=user, status=Order.Status.DELIVERED)
    OrderItemFactory(order=order, product=product)

    url = reverse("api:product-reviews-list", kwargs={"slug": product.slug})
    data = {"rating": 5, "comment": "Excellent quality!"}

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_201_CREATED

    res_data = cast(dict, res.data)
    assert "id" in res_data
    assert res_data["rating"] == 5
    assert res_data["comment"] == "Excellent quality!"
    assert res_data["user"]["username"] == user.username

    # Verify review database status
    review = Review.objects.get(product=product, user=user)
    assert review.status == Review.Status.PENDING
    assert review.comment == "Excellent quality!"


@pytest.mark.django_db
def test_create_review_duplicate_fails(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    user = auth_client.user

    # Purchase the product
    order = OrderFactory(user=user, status=Order.Status.DELIVERED)
    OrderItemFactory(order=order, product=product)

    # Already submitted a review
    ReviewFactory(product=product, user=user, status=Review.Status.APPROVED)

    url = reverse("api:product-reviews-list", kwargs={"slug": product.slug})
    data = {"rating": 4, "comment": "Another review."}

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_review_invalid_rating(auth_client: AuthClient) -> None:
    product = ProductFactory(slug="nice-beer")
    user = auth_client.user

    order = OrderFactory(user=user, status=Order.Status.DELIVERED)
    OrderItemFactory(order=order, product=product)

    url = reverse("api:product-reviews-list", kwargs={"slug": product.slug})

    # Rating 6 is invalid (above max)
    res = cast(Response, auth_client.post(url, {"rating": 6, "comment": "OK"}, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    # Rating 0 is invalid (below min)
    res_zero = cast(Response, auth_client.post(url, {"rating": 0, "comment": "OK"}, format="json"))
    assert res_zero.status_code == status.HTTP_400_BAD_REQUEST
