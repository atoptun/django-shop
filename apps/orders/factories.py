import factory

from apps.accounts.factories import UserFactory
from apps.orders.models import Order, OrderItem
from apps.products.factories import ProductFactory


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
