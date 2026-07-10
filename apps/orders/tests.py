import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.orders.factories import OrderFactory, OrderItemFactory
from apps.orders.models import Order
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


def test_checkout_view(client):
    url = reverse("orders:checkout")

    # Unauthenticated guest should redirect to login
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url

    # Authenticated user should load checkout page successfully if cart is not empty
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory()
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 1})

    response = client.get(url)
    assert response.status_code == 200
    assert "orders/checkout.html" in [t.name for t in response.templates]


# --- Signal Integration Test ---


def test_login_triggers_cart_merge(client):
    product = ProductFactory()
    session = client.session
    session["cart"] = {product.slug: 3}
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


# --- Stock Limit Tests ---


def test_cart_service_stock_limit():
    product = ProductFactory(stock=5)

    # Guest cart stock check
    request = get_mock_request(user=None)
    service = CartService(request)

    # Adding within stock passes
    service.add(product.slug, 4)
    assert service.get_product_quantity(product.slug) == 4

    # Exceeding stock raises ValueError
    with pytest.raises(ValueError) as excinfo:
        service.add(product.slug, 2)
    assert "Only 5 items are available in stock." in str(excinfo.value)

    # Updating within stock passes
    service.update(product.slug, 5)
    assert service.get_product_quantity(product.slug) == 5

    # Updating exceeding stock raises ValueError
    with pytest.raises(ValueError):
        service.update(product.slug, 6)


def test_update_cart_view_stock_limit_ajax(client):
    product = ProductFactory(stock=2)
    url = reverse("cart:update_cart", kwargs={"product_slug": product.slug})

    session = client.session
    session["cart"] = {product.slug: 2}
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


def test_checkout_submit_success(client):
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(price=10.00, stock=5)
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 2})

    from apps.payments.models import PaymentMethod

    method = PaymentMethod.objects.get(code="debit")

    checkout_url = reverse("orders:checkout")
    response = client.post(
        checkout_url,
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": method.pk,
            "card_number": "4000 0000 0000 0005",
            "cvv": "000",
        },
    )
    assert response.status_code == 302
    from apps.orders.models import Order

    order = Order.objects.get(user=user)
    assert response.url == reverse("payments:pay", kwargs={"order_uuid": order.uuid})
    assert order.status == Order.Status.PENDING
    assert order.total_price == 20.00
    assert "Jane Doe" in order.shipping_address

    product.refresh_from_db()
    assert product.stock == 3

    cart_service = CartService(get_mock_request(user=user))
    assert cart_service.get_total_items() == 0


def test_checkout_submit_out_of_stock(client):
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(price=10.00, stock=1)
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 1})

    # Simulate race condition where stock becomes 0
    product.stock = 0
    product.save()

    from apps.payments.models import PaymentMethod

    method = PaymentMethod.objects.get(code="debit")

    checkout_url = reverse("orders:checkout")
    response = client.post(
        checkout_url,
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": method.pk,
            "card_number": "4000 0000 0000 0002",
            "cvv": "123",
        },
    )
    assert response.status_code == 200
    assert f"Not enough stock for {product.name}" in response.content.decode()

    from apps.orders.models import Order

    assert Order.objects.filter(user=user).exists() is False


def test_order_cancelled_replenishes_stock():
    from apps.orders.services import OrderService

    product = ProductFactory(stock=10)
    order = OrderFactory(total_price=10.00)
    OrderItemFactory(order=order, product=product, quantity=3)

    OrderService.cancel_order(order)

    product.refresh_from_db()
    assert product.stock == 13


def test_checkout_emails_sent(client):
    from django.core import mail

    mail.outbox.clear()

    user = UserFactory(email="buyer@example.com")
    client.force_login(user)

    product = ProductFactory(price=5.00, stock=10)
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 1})

    from apps.payments.models import PaymentMethod

    method = PaymentMethod.objects.get(code="debit")

    checkout_url = reverse("orders:checkout")
    client.post(
        checkout_url,
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": method.pk,
            "card_number": "4000 0000 0000 0002",
            "cvv": "123",
        },
    )

    assert len(mail.outbox) == 2
    buyer_email = mail.outbox[0]
    assert buyer_email.to == ["buyer@example.com"]
    assert "Order Confirmation" in buyer_email.subject

    admin_email = mail.outbox[1]
    assert "New Order Placed" in admin_email.subject


def test_admin_order_item_inline_formset():
    from django.forms import inlineformset_factory

    from apps.orders.admin import OrderItemInlineFormSet
    from apps.orders.models import OrderItem

    user = UserFactory()
    order = OrderFactory(user=user, total_price=100.00)
    product1 = ProductFactory(stock=10, price=10.00)
    item = OrderItemFactory(order=order, product=product1, quantity=3, price=10.00)

    # Initial stock verify
    assert product1.stock == 10

    # Inline formset factory
    OrderItemFormSet = inlineformset_factory(
        Order,
        OrderItem,
        formset=OrderItemInlineFormSet,
        fields=["product", "quantity"],
        extra=1,
        can_delete=True,
    )

    # 1. Edit quantity from 3 to 5 (valid)
    data = {
        "items-TOTAL_FORMS": "2",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(item.id),
        "items-0-product": str(product1.id),
        "items-0-quantity": "5",
        "items-1-id": "",
        "items-1-product": "",
        "items-1-quantity": "",
    }
    formset = OrderItemFormSet(data, instance=order, prefix="items")
    assert formset.is_valid()
    formset.save()

    product1.refresh_from_db()
    assert product1.stock == 8  # 2 more reserved
    order.refresh_from_db()
    assert order.total_price == 50.00  # 5 * 10

    # 2. Edit quantity to 20 (invalid - exceeds stock 8 + 5 = 13)
    data["items-0-quantity"] = "20"
    formset = OrderItemFormSet(data, instance=order, prefix="items")
    assert formset.is_valid() is False
    assert "Insufficient stock" in str(formset.non_form_errors())

    # 3. Add a new item inline
    product2 = ProductFactory(stock=5, price=20.00)
    data = {
        "items-TOTAL_FORMS": "2",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(item.id),
        "items-0-product": str(product1.id),
        "items-0-quantity": "5",
        "items-1-id": "",
        "items-1-product": str(product2.id),
        "items-1-quantity": "2",
    }
    formset = OrderItemFormSet(data, instance=order, prefix="items")
    assert formset.is_valid()
    formset.save()

    product2.refresh_from_db()
    assert product2.stock == 3  # 2 reserved
    order.refresh_from_db()
    assert order.total_price == 90.00  # (5 * 10) + (2 * 20)

    # 4. Delete an item inline
    data = {
        "items-TOTAL_FORMS": "2",
        "items-INITIAL_FORMS": "2",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(item.id),
        "items-0-product": str(product1.id),
        "items-0-quantity": "5",
        "items-0-DELETE": "on",  # Mark for deletion
        "items-1-id": str(order.items.exclude(id=item.id).first().id),
        "items-1-product": str(product2.id),
        "items-1-quantity": "2",
    }
    formset = OrderItemFormSet(data, instance=order, prefix="items")
    assert formset.is_valid()
    formset.save()

    product1.refresh_from_db()
    assert product1.stock == 13  # 5 returned
    order.refresh_from_db()
    assert order.total_price == 40.00  # only product2 remains (2 * 20)


def test_admin_order_readonly_final_states():
    from django.contrib.admin.sites import AdminSite

    from apps.orders.admin import OrderAdmin

    user = UserFactory()
    order = OrderFactory(user=user, status=Order.Status.SHIPPED, total_price=10.00)

    site = AdminSite()
    admin_obj = OrderAdmin(Order, site)

    # Check that when order is SHIPPED, all fields are read-only
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/admin/")
    request.user = UserFactory(is_superuser=True)

    readonly = admin_obj.get_readonly_fields(request, order)
    # Check some fields are in readonly
    assert "status" in readonly
    assert "total_price" in readonly


def test_admin_order_item_inline_non_pending_readonly():
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.orders.admin import OrderItemInline

    user = UserFactory()
    order = OrderFactory(user=user, status=Order.Status.PAID, total_price=10.00)

    site = AdminSite()
    inline_obj = OrderItemInline(Order, site)

    rf = RequestFactory()
    request = rf.get("/admin/")
    request.user = UserFactory(is_superuser=True)

    # Check permission restrictions for non-PENDING status
    assert inline_obj.has_add_permission(request, order) is False
    assert inline_obj.has_delete_permission(request, order) is False

    readonly = inline_obj.get_readonly_fields(request, order)
    assert "product" in readonly
    assert "quantity" in readonly
    assert "price" in readonly


# --- Forms and Views Edge-Case Coverage ---


def test_checkout_form_address_choices_anonymous():
    from apps.orders.forms import CheckoutForm

    form = CheckoutForm(user=None)
    assert form.fields["address_choice"].choices == [("new", "Enter address details below")]


def test_checkout_form_invalid_saved_address_id():
    from apps.orders.forms import CheckoutForm

    user = UserFactory()
    # Post with an address ID that does not exist for this user
    form = CheckoutForm(
        data={
            "address_choice": "9999",
            "payment_method": "debit",
        },
        user=user,
    )
    form.fields["address_choice"].choices.append(("9999", "Fake Address"))
    assert form.is_valid() is False
    assert "address_choice" in form.errors
    err_msg = "Selected address is invalid or does not belong to you."
    assert err_msg in form.errors["address_choice"][0]


def test_checkout_form_value_error_address():
    from apps.orders.forms import CheckoutForm

    user = UserFactory()
    # Post with an address choice that cannot be converted to int and is not "new"
    form = CheckoutForm(
        data={
            "address_choice": "not-a-number-or-new",
            "payment_method": "debit",
        },
        user=user,
    )
    assert form.is_valid() is False
    assert "address_choice" in form.errors


def test_checkout_form_missing_new_address_fields():
    from apps.orders.forms import CheckoutForm

    user = UserFactory()
    form = CheckoutForm(
        data={
            "address_choice": "new",
            "payment_method": "debit",
        },
        user=user,
    )
    assert form.is_valid() is False
    for field in ["full_name", "phone", "city", "address"]:
        assert field in form.errors


def test_checkout_empty_cart_redirect(client):
    """Verify checkout page redirects to cart detail when the cart is empty."""
    user = UserFactory()
    client.force_login(user)

    url = reverse("orders:checkout")

    # GET request
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("cart:cart_detail")

    # POST request
    response = client.post(url, {"shipping_address": "Test Address", "payment_method": 999})
    assert response.status_code == 302
    assert response.url == reverse("cart:cart_detail")


def test_checkout_invalid_form(client):
    """Verify checkout page re-renders form with errors when data is invalid."""
    user = UserFactory()
    client.force_login(user)

    # Seed product and add to cart to avoid empty cart redirect
    product = ProductFactory(price=10.00, stock=5)
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 1})

    url = reverse("orders:checkout")
    # Post with missing address fields
    response = client.post(
        url,
        {
            "address_choice": "new",
            "full_name": "",  # missing
            "phone": "",
            "city": "",
            "address": "",
            "payment_method": 999,
        },
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert "full_name" in form.errors


def test_checkout_invalid_payment_method(client):
    """Verify checkout page re-renders when an invalid/inactive payment method is chosen."""
    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(price=10.00, stock=5)
    client.post(reverse("cart:add_to_cart", kwargs={"product_slug": product.slug}), {"quantity": 1})

    url = reverse("orders:checkout")
    response = client.post(
        url,
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": 9999,  # invalid method ID
        },
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert "payment_method" in form.errors
