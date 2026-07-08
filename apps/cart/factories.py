import factory

from apps.accounts.factories import UserFactory
from apps.cart.models import Cart, CartItem
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
