import pytest
from django.urls import reverse
from rest_framework import status

from apps.products.factories import CategoryFactory, ProductFactory


@pytest.mark.django_db
def test_categories_list_nested(api_client):
    parent = CategoryFactory(name="Parent Cat", slug="parent")
    CategoryFactory(name="Child Cat", slug="child", parent=parent)

    url = reverse("api:categories-list")
    res = api_client.get(url)

    assert res.status_code == status.HTTP_200_OK
    data = res.data["results"]
    assert len(data) == 1
    assert data[0]["slug"] == "parent"
    assert len(data[0]["children"]) == 1
    assert data[0]["children"][0]["slug"] == "child"


@pytest.mark.django_db
def test_product_list_and_detail(api_client):
    product = ProductFactory(name="Beer Lager", price=15.00, stock=5)

    # 1. Test List
    url = reverse("api:products-list")
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data["results"]) == 1
    assert res.data["results"][0]["name"] == "Beer Lager"

    # 2. Test Detail
    url_detail = reverse("api:products-detail", kwargs={"pk": product.id})
    res_detail = api_client.get(url_detail)
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.data["price"] == "15.00"


@pytest.mark.django_db
def test_product_filter_by_price(api_client):
    ProductFactory(price=10.00)
    ProductFactory(price=25.00)
    ProductFactory(price=50.00)

    url = reverse("api:products-list")

    # Min price filter
    res = api_client.get(url, {"min_price": 20.00})
    assert len(res.data["results"]) == 2

    # Max price filter
    res = api_client.get(url, {"max_price": 30.00})
    assert len(res.data["results"]) == 2

    # Combined min/max price filter
    res = api_client.get(url, {"min_price": 15.00, "max_price": 30.00})
    assert len(res.data["results"]) == 1
    assert float(res.data["results"][0]["price"]) == 25.00


@pytest.mark.django_db
def test_product_filter_by_category(api_client):
    cat1 = CategoryFactory(slug="beer")
    cat2 = CategoryFactory(slug="wine")

    ProductFactory(category=cat1)
    ProductFactory(category=cat2)

    url = reverse("api:products-list")
    res = api_client.get(url, {"category_slug": "beer"})
    assert len(res.data["results"]) == 1
    assert res.data["results"][0]["category_slug"] == "beer"


@pytest.mark.django_db
def test_product_filter_in_stock(api_client):
    ProductFactory(stock=0)
    ProductFactory(stock=10)

    url = reverse("api:products-list")
    res = api_client.get(url, {"in_stock": "true"})
    assert len(res.data["results"]) == 1
    assert res.data["results"][0]["stock"] == 10


@pytest.mark.django_db
def test_product_search(api_client):
    ProductFactory(name="Stout Beer", description="Dark malt beer")
    ProductFactory(name="IPA Beer", description="Hoppy beer")

    url = reverse("api:products-list")
    res = api_client.get(url, {"search": "Dark"})
    assert len(res.data["results"]) == 1
    assert "Stout" in res.data["results"][0]["name"]


@pytest.mark.django_db
def test_product_ordering(api_client):
    ProductFactory(price=50.00)
    ProductFactory(price=10.00)
    ProductFactory(price=30.00)

    url = reverse("api:products-list")

    # Order ascending
    res = api_client.get(url, {"ordering": "price"})
    prices = [float(p["price"]) for p in res.data["results"]]
    assert prices == [10.00, 30.00, 50.00]

    # Order descending
    res = api_client.get(url, {"ordering": "-price"})
    prices = [float(p["price"]) for p in res.data["results"]]
    assert prices == [50.00, 30.00, 10.00]
