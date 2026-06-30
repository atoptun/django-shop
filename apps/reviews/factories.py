import factory

from apps.accounts.factories import UserFactory
from apps.products.factories import ProductFactory

from .models import Review


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)  # type: ignore
    user = factory.SubFactory(UserFactory)  # type: ignore
    rating = 5
    comment = factory.Faker("text")  # type: ignore
