import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.cart.factories import CartFactory, CartItemFactory
from apps.cart.models import Cart, CartItem
from apps.products.factories import ProductFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    user = UserFactory(email="testuser@example.com")
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    api_client.user = user
    return api_client


# =============================================================================
# UNAUTHENTICATED SCENARIO
# =============================================================================


@pytest.mark.django_db
def test_cart_access_unauthenticated(api_client):
    url = reverse("api:cart-list")
    res = api_client.get(url)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# AUTHENTICATED SCENARIOS
# =============================================================================


@pytest.mark.django_db
def test_get_cart_empty_authenticated(auth_client):
    url = reverse("api:cart-list")
    res = auth_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["total_items"] == 0
    assert float(res.data["total_price"]) == 0.00
    assert len(res.data["items"]) == 0


@pytest.mark.django_db
def test_add_to_cart_success(auth_client):
    product = ProductFactory(price=15.50, stock=10)
    url = reverse("api:cart-list")
    data = {"product_id": product.id, "quantity": 3}

    res = auth_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["quantity"] == 3
    assert res.data["product"]["name"] == product.name

    # Verify database state
    cart = Cart.objects.get(user=auth_client.user)
    item = CartItem.objects.get(cart=cart, product=product)
    assert item.quantity == 3


@pytest.mark.django_db
def test_add_to_cart_insufficient_stock(auth_client):
    product = ProductFactory(price=10.00, stock=2)
    url = reverse("api:cart-list")
    data = {"product_id": product.id, "quantity": 5}

    res = auth_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in res.data or "quantity" in res.data


@pytest.mark.django_db
def test_add_to_cart_invalid_product(auth_client):
    url = reverse("api:cart-list")
    data = {"product_id": 99999, "quantity": 1}

    res = auth_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_cart_item_quantity_success(auth_client):
    product = ProductFactory(price=12.00, stock=15)
    cart = CartFactory(user=auth_client.user)
    CartItemFactory(cart=cart, product=product, quantity=2)

    # Endpoint: PUT /api/cart/items/{product_id}/
    url = reverse("api:cart-items-detail", kwargs={"product_id": product.id})
    data = {"quantity": 5}

    res = auth_client.put(url, data, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["quantity"] == 5

    item = CartItem.objects.get(cart=cart, product=product)
    assert item.quantity == 5


@pytest.mark.django_db
def test_update_cart_item_quantity_exceed_stock(auth_client):
    product = ProductFactory(price=12.00, stock=5)
    cart = CartFactory(user=auth_client.user)
    CartItemFactory(cart=cart, product=product, quantity=2)

    url = reverse("api:cart-items-detail", kwargs={"product_id": product.id})
    data = {"quantity": 10}

    res = auth_client.put(url, data, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_delete_cart_item_success(auth_client):
    product = ProductFactory()
    cart = CartFactory(user=auth_client.user)
    CartItemFactory(cart=cart, product=product, quantity=2)

    # Endpoint: DELETE /api/cart/items/{product_id}/
    url = reverse("api:cart-items-detail", kwargs={"product_id": product.id})

    res = auth_client.delete(url)
    assert res.status_code == status.HTTP_204_NO_CONTENT
    assert CartItem.objects.filter(cart=cart, product=product).exists() is False
