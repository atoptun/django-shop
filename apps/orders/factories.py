import factory

from apps.accounts.factories import UserFactory
from apps.orders.models import Cart, CartItem, Order, OrderItem, Payment, PaymentMethod
from apps.products.factories import ProductFactory


class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)  # type: ignore


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)  # type: ignore
    product = factory.SubFactory(ProductFactory)  # type: ignore
    quantity = 1


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)  # type: ignore
    status = Order.Status.PENDING
    total_price = 10.00
    shipping_address = "Test shipping address"


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)  # type: ignore
    product = factory.SubFactory(ProductFactory)  # type: ignore
    quantity = 1
    price = 10.00


class PaymentMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentMethod

    code = "debit"
    name = "Debit Card"
    is_active = True


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)  # type: ignore
    payment_method = factory.SubFactory(PaymentMethodFactory)  # type: ignore
    transaction_id = factory.Sequence(lambda n: f"txn_{n}")  # type: ignore
