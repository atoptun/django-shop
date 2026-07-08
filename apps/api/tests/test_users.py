import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import AddressFactory, UserFactory
from apps.accounts.models import Address


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    user = UserFactory(email="testuser@example.com")
    user.profile.phone = "+380991234567"
    user.profile.city = "Kyiv"
    user.profile.address = "Test St 123"
    user.profile.save()

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    api_client.user = user
    return api_client


# =============================================================================
# USER AUTHENTICATION TESTS
# =============================================================================


@pytest.mark.django_db
def test_user_registration_success(api_client):
    url = reverse("api:user-register")
    data = {
        "email": "newuser@example.com",
        "password": "strongpassword123",
        "first_name": "Alice",
        "last_name": "Smith",
        "profile": {"phone": "+380507654321", "city": "Lviv", "address": "Shevchenka St 10"},
    }
    res = api_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert "user" in res.data
    assert res.data["user"]["email"] == "newuser@example.com"
    assert "tokens" in res.data
    assert "access" in res.data["tokens"]


@pytest.mark.django_db
def test_user_registration_duplicate_email(api_client):
    UserFactory(email="duplicate@example.com")
    url = reverse("api:user-register")
    data = {
        "email": "duplicate@example.com",
        "password": "password123",
    }
    res = api_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_user_login_success(api_client):
    UserFactory(email="login@example.com", password="correct_password")
    url = reverse("api:user-login")
    data = {"username": "login@example.com", "password": "correct_password"}
    res = api_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert "access" in res.data
    assert "refresh" in res.data


@pytest.mark.django_db
def test_user_login_failure(api_client):
    UserFactory(email="login@example.com", password="correct_password")
    url = reverse("api:user-login")
    data = {"username": "login@example.com", "password": "wrong_password"}
    res = api_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# USER PROFILE TESTS
# =============================================================================


@pytest.mark.django_db
def test_get_profile_unauthenticated(api_client):
    url = reverse("api:user-detail")
    res = api_client.get(url)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_get_profile_authenticated(auth_client):
    url = reverse("api:user-detail")
    res = auth_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["email"] == "testuser@example.com"
    assert res.data["profile"]["city"] == "Kyiv"


@pytest.mark.django_db
def test_update_profile_authenticated(auth_client):
    url = reverse("api:user-detail")
    data = {
        "first_name": "UpdatedName",
        "profile": {"phone": "+380509998877", "city": "Odesa", "address": "Deribasivska St 1"},
    }
    res = auth_client.put(url, data, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["first_name"] == "UpdatedName"
    assert res.data["profile"]["city"] == "Odesa"

    auth_client.user.refresh_from_db()
    assert auth_client.user.first_name == "UpdatedName"
    assert auth_client.user.profile.city == "Odesa"


# =============================================================================
# USER ADDRESSES TESTS
# =============================================================================


@pytest.mark.django_db
def test_list_addresses_only_own(auth_client):
    AddressFactory(user=auth_client.user)
    other_user = UserFactory()
    AddressFactory(user=other_user)

    url = reverse("api:user-addresses-list")
    res = auth_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data["results"]) == 1


@pytest.mark.django_db
def test_create_single_address(auth_client):
    url = reverse("api:user-addresses-list")
    data = {
        "recipient_name": "Bob",
        "phone": "+380998887766",
        "city": "Dnipro",
        "address_line": "Central Ave 5",
    }
    res = auth_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert Address.objects.filter(user=auth_client.user).count() == 1


@pytest.mark.django_db
def test_create_bulk_addresses(auth_client):
    url = reverse("api:user-addresses-list")
    data = [
        {
            "recipient_name": "Bob 1",
            "phone": "+380998887766",
            "city": "Dnipro",
            "address_line": "Central Ave 5",
        },
        {
            "recipient_name": "Bob 2",
            "phone": "+380998887767",
            "city": "Dnipro",
            "address_line": "Central Ave 6",
        },
    ]
    res = auth_client.post(url, data, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert len(res.data) == 2
    assert Address.objects.filter(user=auth_client.user).count() == 2


@pytest.mark.django_db
def test_retrieve_other_user_address_not_found(auth_client):
    other_user = UserFactory()
    other_address = AddressFactory(user=other_user)

    url = reverse("api:user-addresses-detail", kwargs={"pk": other_address.id})
    res = auth_client.get(url)
    assert res.status_code == status.HTTP_404_NOT_FOUND
