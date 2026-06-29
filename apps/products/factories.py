import factory

from apps.products.models import Category, Product


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")  # type: ignore
    slug = factory.Sequence(lambda n: f"category-{n}")  # type: ignore


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")  # type: ignore
    slug = factory.Sequence(lambda n: f"product-{n}")  # type: ignore
    description = "Test product description"
    price = 10.00
    category = factory.SubFactory(CategoryFactory)  # type: ignore
    stock = 100
    is_active = True
