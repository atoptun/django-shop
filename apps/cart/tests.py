from decimal import Decimal

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.cart.factories import CartFactory, CartItemFactory
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.products.factories import ProductFactory


def get_mock_request(user=None, session_data=None):
    rf = RequestFactory()
    request = rf.post("/dummy/")

    # Setup session
    middleware = SessionMiddleware(lambda r: None)  # type: ignore
    middleware.process_request(request)
    if session_data:
        request.session.update(session_data)
    else:
        request.session["cart"] = {}
    request.session.save()

    # Setup user
    if user:
        request.user = user
    else:
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()

    return request


@pytest.mark.django_db
def test_guest_cart_lifecycle():
    product1 = ProductFactory(price=10.00)
    product2 = ProductFactory(price=25.00)

    request = get_mock_request(user=None)
    service = CartService(request)

    assert service.get_total_items() == 0
    assert service.get_total_price() == Decimal("0")
    assert len(service.get_items()) == 0

    assert service.add(product1.pk, 2) == 2
    assert service.add(product2.pk, 1) == 1

    assert service.get_total_items() == 3
    assert service.get_total_price() == Decimal("45.00")
    assert service.get_product_quantity(product1.pk) == 2

    assert service.update(product1.pk, 5) == 5
    assert service.get_total_items() == 6
    assert service.get_total_price() == Decimal("75.00")

    service.remove(product2.pk)
    assert service.get_total_items() == 5
    assert service.get_product_quantity(product2.pk) == 0

    assert service.update(product1.pk, 0) == 0
    assert service.get_total_items() == 0


@pytest.mark.django_db
def test_db_cart_lifecycle():
    user = UserFactory()
    product1 = ProductFactory(price=15.00)
    product2 = ProductFactory(price=30.00)

    request = get_mock_request(user=user)
    service = CartService(request)

    assert service.add(product1.pk, 1) == 1
    assert service.add(product2.pk, 2) == 2

    assert service.get_total_items() == 3
    assert service.get_total_price() == Decimal("75.00")
    assert Cart.objects.filter(user=user).exists() is True

    assert service.update(product1.pk, 3) == 3
    assert service.get_total_items() == 5

    service.remove(product2.pk)
    assert service.get_total_items() == 3

    assert service.update(product1.pk, 0) == 0
    assert service.get_total_items() == 0


@pytest.mark.django_db
def test_merge_session_cart():
    user = UserFactory()
    product1 = ProductFactory(price=10.00)
    product2 = ProductFactory(price=20.00)

    session_data = {"cart": {str(product1.pk): 3, str(product2.pk): 1}}
    request = get_mock_request(user=user, session_data=session_data)

    db_cart = CartFactory(user=user)
    CartItemFactory(cart=db_cart, product=product1, quantity=1)

    service = CartService(request)
    service.merge_session_cart()

    assert CartItem.objects.get(cart=db_cart, product=product1).quantity == 4
    assert CartItem.objects.get(cart=db_cart, product=product2).quantity == 1
    assert service.get_total_items() == 5
    assert request.session["cart"] == {}


@pytest.mark.django_db
def test_cart_item_subtotal():
    product = ProductFactory(price=11.11)
    cart_item = CartItemFactory(product=product, quantity=5)

    assert cart_item.subtotal == 55.55


@pytest.mark.django_db
def test_cart_view(client):
    url = reverse("cart:cart_detail")

    # Unauthenticated guest
    response = client.get(url)
    assert response.status_code == 200
    assert "cart/cart.html" in [t.name for t in response.templates]

    # Authenticated user
    user = UserFactory()
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_to_cart_view_redirect(client):
    product = ProductFactory()
    url = reverse("cart:add_to_cart", kwargs={"product_id": product.id})

    response = client.post(url, {"quantity": 2})
    assert response.status_code == 302
    assert response.url == reverse("cart:cart_detail")
    assert client.session["cart"][str(product.id)] == 2


@pytest.mark.django_db
def test_add_to_cart_view_ajax(client):
    product = ProductFactory()
    url = reverse("cart:add_to_cart", kwargs={"product_id": product.id})

    response = client.post(
        url,
        {"quantity": 3},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["product_quantity"] == 3
    assert data["cart_total_items"] == 3


@pytest.mark.django_db
def test_update_cart_view_ajax(client):
    product = ProductFactory(price=10.00)
    url = reverse("cart:update_cart", kwargs={"product_id": product.id})

    session = client.session
    session["cart"] = {str(product.id): 2}
    session.save()

    response = client.post(
        url,
        {"action": "increase"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_quantity"] == 3
    assert data["item_subtotal"] == "$30.00"
    assert data["cart_total_price"] == "$30.00"


@pytest.mark.django_db
def test_update_cart_view_invalid_action(client):
    product = ProductFactory()
    url = reverse("cart:update_cart", kwargs={"product_id": product.id})

    # Missing action should return 400
    response = client.post(url)
    assert response.status_code == 400

    # Invalid action should return 400
    response = client.post(url, {"action": "invalid"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_remove_from_cart_view_ajax(client):
    product = ProductFactory()
    url = reverse("cart:remove_from_cart", kwargs={"product_id": product.id})

    session = client.session
    session["cart"] = {str(product.id): 5}
    session.save()

    response = client.post(
        url,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["product_quantity"] == 0
    assert data["cart_total_items"] == 0


@pytest.mark.django_db
def test_update_cart_view_stock_limit_ajax(client):
    product = ProductFactory(stock=2)
    url = reverse("cart:update_cart", kwargs={"product_id": product.id})

    session = client.session
    session["cart"] = {str(product.id): 2}
    session.save()

    response = client.post(
        url,
        {"action": "increase"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Only 2 items are available in stock." in data["error"]


@pytest.mark.django_db
def test_add_to_cart_ajax_value_error(client):
    product = ProductFactory(stock=2)
    url = reverse("cart:add_to_cart", kwargs={"product_id": product.id})

    response = client.post(
        url,
        {"quantity": "5"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Only 2 items are available in stock." in data["error"]


@pytest.mark.django_db
def test_update_cart_ajax_value_error(client):
    product = ProductFactory(stock=2)
    url = reverse("cart:update_cart", kwargs={"product_id": product.id})

    session = client.session
    session["cart"] = {str(product.id): 2}
    session.save()

    response = client.post(
        url,
        {"action": "increase"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False


@pytest.mark.django_db
def test_update_cart_non_existent_product_ajax(client):
    session = client.session
    session["cart"] = {"99999": 1}
    session.save()

    url = reverse("cart:update_cart", kwargs={"product_id": 99999})
    response = client.post(
        url,
        {"action": "increase"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Product does not exist" in data["error"]
