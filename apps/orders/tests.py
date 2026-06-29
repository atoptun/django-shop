import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.orders.factories import (
    CartFactory,
    CartItemFactory,
    OrderFactory,
    OrderItemFactory,
    PaymentFactory,
)
from apps.orders.models import Cart, CartItem, Order, Payment
from apps.orders.services import CartService
from apps.products.factories import ProductFactory

User = get_user_model()
pytestmark = pytest.mark.django_db


# --- Request Mock Helper ---
def get_mock_request(user=None, session_data=None):
    rf = RequestFactory()
    request = rf.post("/dummy/")

    # Setup session
    middleware = SessionMiddleware(lambda r: None)
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


# --- CartService Tests ---


def test_guest_cart_lifecycle():
    product1 = ProductFactory(price=10.00)
    product2 = ProductFactory(price=25.00)

    # Initial guest request
    request = get_mock_request(user=None)
    service = CartService(request)

    # Assert empty state
    assert service.get_total_items() == 0
    assert service.get_total_price() == 0
    assert len(service.get_items()) == 0

    # Add items
    assert service.add(product1.id, 2) == 2
    assert service.add(product2.id, 1) == 1

    # Verify totals
    assert service.get_total_items() == 3
    assert service.get_total_price() == 45.00
    assert service.get_product_quantity(product1.id) == 2

    # Update item
    assert service.update(product1.id, 5) == 5
    assert service.get_total_items() == 6
    assert service.get_total_price() == 75.00

    # Remove item
    service.remove(product2.id)
    assert service.get_total_items() == 5
    assert service.get_product_quantity(product2.id) == 0

    # Zero updates removes item
    assert service.update(product1.id, 0) == 0
    assert service.get_total_items() == 0


def test_db_cart_lifecycle():
    user = UserFactory()
    product1 = ProductFactory(price=15.00)
    product2 = ProductFactory(price=30.00)

    request = get_mock_request(user=user)
    service = CartService(request)

    # Add items
    assert service.add(product1.id, 1) == 1
    assert service.add(product2.id, 2) == 2

    # Verify totals
    assert service.get_total_items() == 3
    assert service.get_total_price() == 75.00
    assert Cart.objects.filter(user=user).exists() is True

    # Update quantity
    assert service.update(product1.id, 3) == 3
    assert service.get_total_items() == 5

    # Remove item
    service.remove(product2.id)
    assert service.get_total_items() == 3

    # Zero update removes item
    assert service.update(product1.id, 0) == 0
    assert service.get_total_items() == 0


def test_merge_session_cart():
    user = UserFactory()
    product1 = ProductFactory(price=10.00)
    product2 = ProductFactory(price=20.00)

    # 1. Guest cart setup
    session_data = {"cart": {str(product1.id): 3, str(product2.id): 1}}
    request = get_mock_request(user=user, session_data=session_data)

    # 2. Existing DB cart setup (already contains 1 unit of product1)
    db_cart = CartFactory(user=user)
    CartItemFactory(cart=db_cart, product=product1, quantity=1)

    # 3. Perform merge
    service = CartService(request)
    service.merge_session_cart()

    # 4. Assert DB cart updated (product1: 1+3=4, product2: 1)
    assert CartItem.objects.get(cart=db_cart, product=product1).quantity == 4
    assert CartItem.objects.get(cart=db_cart, product=product2).quantity == 1
    assert service.get_total_items() == 5

    # 5. Assert session cleared
    assert request.session["cart"] == {}


# --- Model Tests ---


def test_order_model():
    user = UserFactory(email="buyer@example.com")
    order = OrderFactory(user=user, status=Order.Status.PAID, total_price=99.99)

    assert order.user == user
    assert order.status == Order.Status.PAID
    assert order.total_price == 99.99
    assert str(order) == f"Order #{order.pk} by buyer@example.com"


def test_order_item_model():
    order = OrderFactory()
    product = ProductFactory(price=12.50)
    order_item = OrderItemFactory(order=order, product=product, price=12.50, quantity=3)

    assert order_item.order == order
    assert order_item.product == product
    assert order_item.subtotal == 37.50
    assert str(order_item) == f"3 x {product.name}"


def test_payment_model():
    order = OrderFactory()
    payment = PaymentFactory(order=order, method=Payment.Method.PAYPAL, transaction_id="TX_123")

    assert payment.order == order
    assert payment.method == Payment.Method.PAYPAL
    assert payment.transaction_id == "TX_123"
    assert str(payment) == f"Payment for Order #{order.pk} via paypal"


def test_cart_item_subtotal():
    product = ProductFactory(price=11.11)
    cart_item = CartItemFactory(product=product, quantity=5)

    assert cart_item.subtotal == 55.55


# --- View Tests ---


def test_cart_view(client):
    url = reverse("orders:cart")

    # Unauthenticated guest
    response = client.get(url)
    assert response.status_code == 200
    assert "orders/cart.html" in [t.name for t in response.templates]

    # Authenticated user
    user = UserFactory()
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200


def test_add_to_cart_view_redirect(client):
    product = ProductFactory()
    url = reverse("orders:add_to_cart", kwargs={"product_id": product.id})

    response = client.post(url, {"quantity": 2})
    assert response.status_code == 302
    assert response.url == reverse("orders:cart")

    # Verify session cart updated
    assert client.session["cart"][str(product.id)] == 2


def test_add_to_cart_view_ajax(client):
    product = ProductFactory()
    url = reverse("orders:add_to_cart", kwargs={"product_id": product.id})

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


def test_update_cart_view_ajax(client):
    product = ProductFactory(price=10.00)
    url = reverse("orders:update_cart", kwargs={"product_id": product.id})

    # Guest session setup
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


def test_update_cart_view_invalid_action(client):
    product = ProductFactory()
    url = reverse("orders:update_cart", kwargs={"product_id": product.id})

    # Missing action should return 400
    response = client.post(url)
    assert response.status_code == 400

    # Invalid action should return 400
    response = client.post(url, {"action": "invalid"})
    assert response.status_code == 400


def test_remove_from_cart_view_ajax(client):
    product = ProductFactory()
    url = reverse("orders:remove_from_cart", kwargs={"product_id": product.id})

    # Guest session setup
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


def test_checkout_view(client):
    url = reverse("orders:checkout")

    # Unauthenticated guest should redirect to login
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url

    # Authenticated user should load checkout page successfully
    user = UserFactory()
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    assert "orders/checkout.html" in [t.name for t in response.templates]


# --- Signal Integration Test ---


def test_login_triggers_cart_merge(client):
    product = ProductFactory()
    session = client.session
    session["cart"] = {str(product.id): 3}
    session.save()

    # Authenticate user via POST request to login endpoint
    user = UserFactory(email="guest-buyer@example.com")
    url = reverse("accounts:login")
    client.post(url, {"username": "guest-buyer@example.com", "password": "password123"})

    # Check database cart was created and session merged
    assert Cart.objects.filter(user=user).exists() is True
    db_cart = Cart.objects.get(user=user)
    assert CartItem.objects.filter(cart=db_cart, product=product).exists() is True
    assert CartItem.objects.get(cart=db_cart, product=product).quantity == 3

    # Check session cleared after login
    assert "cart" in client.session
    assert client.session["cart"] == {}
