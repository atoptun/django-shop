import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.products.factories import CategoryFactory, ProductFactory
from apps.reviews.factories import ReviewFactory

pytestmark = pytest.mark.django_db


# --- Model Tests ---


def test_category_validation() -> None:
    category = CategoryFactory(name="Tech", slug="")
    assert category.slug == "tech"
    assert str(category) == "Tech"

    # Category cannot be its own parent
    category.parent = category
    with pytest.raises(ValueError, match="A category cannot be its own parent."):
        category.save()


def test_product_validation() -> None:
    product = ProductFactory(name="Laptop Pro", slug="")
    assert product.slug == "laptop-pro"
    assert str(product) == "Laptop Pro"
    assert product.get_absolute_url() == reverse("products:detail", kwargs={"slug": "laptop-pro"})


# --- View Tests ---


def test_product_list_view_active_filtering(client) -> None:
    ProductFactory(name="Active Product", is_active=True)
    ProductFactory(name="Inactive Product", is_active=False)

    url = reverse("products:list")
    response = client.get(url)

    assert response.status_code == 200
    products = list(response.context["products"])
    assert len(products) == 1
    assert products[0].name == "Active Product"


def test_product_list_view_search(client) -> None:
    p1 = ProductFactory(name="Keyboard", description="mechanical typing key", is_active=True)
    p2 = ProductFactory(name="Mouse", description="gaming pointing device", is_active=True)

    url = reverse("products:list")

    # Search for Keyboard description snippet
    response = client.get(url, {"search": "typing"})
    assert p1 in response.context["products"]
    assert p2 not in response.context["products"]


def test_product_list_view_categories(client) -> None:
    parent = CategoryFactory(name="Electronics")
    child = CategoryFactory(name="Phones", parent=parent)

    p1 = ProductFactory(category=child, is_active=True)
    p2 = ProductFactory(is_active=True)

    url = reverse("products:list")

    # Filter by parent category
    response = client.get(url, {"category": [parent.slug]})
    assert p1 in response.context["products"]
    assert p2 not in response.context["products"]

    # Filter by child category
    response = client.get(url, {"category": [child.slug]})
    assert p1 in response.context["products"]
    assert p2 not in response.context["products"]


def test_product_list_view_sorting(client) -> None:
    p1 = ProductFactory(price=10.00, average_rating=4.5, is_active=True)
    p2 = ProductFactory(price=20.00, average_rating=3.0, is_active=True)

    url = reverse("products:list")

    # Sort price ascending
    response = client.get(url, {"sort": "price_asc"})
    assert list(response.context["products"]) == [p1, p2]

    # Sort price descending
    response = client.get(url, {"sort": "price_desc"})
    assert list(response.context["products"]) == [p2, p1]

    # Sort rating
    response = client.get(url, {"sort": "rating"})
    assert list(response.context["products"]) == [p1, p2]

    # Invalid sort fallback
    response = client.get(url, {"sort": "invalid"})
    assert response.status_code == 200


def test_product_detail_view_anonymous(client) -> None:
    product = ProductFactory(is_active=True)
    url = product.get_absolute_url()
    response = client.get(url)

    assert response.status_code == 200
    assert response.context["can_review"] is False
    assert "review_form" not in response.context or response.context["review_form"] is None


def test_product_detail_view_can_review(client) -> None:
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(is_active=True)

    # Note: user hasn't bought it yet, so they shouldn't be able to review
    url = product.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["can_review"] is False

    # Mock already reviewed check
    # Let's say we create a review from this user on the product
    ReviewFactory(product=product, user=user)
    response = client.get(url)
    assert response.context["already_reviewed"] is True
