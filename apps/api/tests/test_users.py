from typing import cast

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.accounts.factories import AddressFactory, UserFactory
from apps.accounts.models import Address
from apps.api.tests import AuthClient

# =============================================================================
# USER AUTHENTICATION TESTS
# =============================================================================


@pytest.mark.django_db
def test_user_registration_success(api_client: APIClient) -> None:
    url = reverse("api:user-register")
    data = {
        "email": "newuser@example.com",
        "password": "strongpassword123",
    }
    res = cast(Response, api_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_201_CREATED
    assert isinstance(res.data, dict)
    assert "user" in res.data
    assert res.data["user"]["email"] == "newuser@example.com"
    assert "tokens" in res.data
    assert "access" in res.data["tokens"]


@pytest.mark.django_db
def test_user_registration_duplicate_email(api_client: APIClient) -> None:
    UserFactory(email="duplicate@example.com")
    url = reverse("api:user-register")
    data = {
        "email": "duplicate@example.com",
        "password": "password123",
    }
    res = cast(Response, api_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_user_login_success(api_client: APIClient) -> None:
    UserFactory(email="login@example.com", password="correct_password")
    url = reverse("api:user-login")
    data = {"username": "login@example.com", "password": "correct_password"}
    res = cast(Response, api_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert "access" in res.data
    assert "refresh" in res.data


@pytest.mark.django_db
def test_user_login_failure(api_client: APIClient) -> None:
    UserFactory(email="login@example.com", password="correct_password")
    url = reverse("api:user-login")
    data = {"username": "login@example.com", "password": "wrong_password"}
    res = cast(Response, api_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# USER PROFILE TESTS
# =============================================================================


@pytest.mark.django_db
def test_get_profile_unauthenticated(api_client: APIClient) -> None:
    url = reverse("api:user-detail")
    res = cast(Response, api_client.get(url))
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_get_profile_authenticated(auth_client: AuthClient) -> None:
    url = reverse("api:user-detail")
    res = cast(Response, auth_client.get(url))
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert res.data["email"] == "testuser@example.com"
    assert res.data["profile"]["city"] == "Kyiv"


@pytest.mark.django_db
def test_update_profile_authenticated(auth_client: AuthClient) -> None:
    url = reverse("api:user-detail")
    data = {
        "first_name": "UpdatedName",
        "profile": {"phone": "+380509998877", "city": "Odesa", "address": "Deribasivska St 1"},
    }
    res = cast(Response, auth_client.put(url, data, format="json"))
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert res.data["first_name"] == "UpdatedName"
    assert res.data["profile"]["city"] == "Odesa"

    auth_client.user.refresh_from_db()
    assert auth_client.user.first_name == "UpdatedName"
    assert auth_client.user.profile.city == "Odesa"  # type: ignore


# =============================================================================
# USER ADDRESSES TESTS
# =============================================================================


@pytest.mark.django_db
def test_list_addresses_only_own(auth_client: AuthClient) -> None:
    AddressFactory(user=auth_client.user)
    other_user = UserFactory()
    AddressFactory(user=other_user)

    url = reverse("api:user-addresses-list")
    res = cast(Response, auth_client.get(url))
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert len(res.data["results"]) == 1


@pytest.mark.django_db
def test_create_single_address(auth_client: AuthClient) -> None:
    url = reverse("api:user-addresses-list")
    data = {
        "recipient_name": "Bob",
        "phone": "+380998887766",
        "city": "Dnipro",
        "address_line": "Central Ave 5",
    }
    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_201_CREATED
    assert Address.objects.filter(user=auth_client.user).count() == 1


@pytest.mark.django_db
def test_create_bulk_addresses(auth_client: AuthClient) -> None:
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
    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_201_CREATED
    assert isinstance(res.data, list)
    assert len(res.data) == 2
    assert Address.objects.filter(user=auth_client.user).count() == 2


@pytest.mark.django_db
def test_retrieve_other_user_address_not_found(auth_client: AuthClient) -> None:
    other_user = UserFactory()
    other_address = AddressFactory(user=other_user)

    url = reverse("api:user-addresses-detail", kwargs={"pk": other_address.id})
    res = cast(Response, auth_client.get(url))
    assert res.status_code == status.HTTP_404_NOT_FOUND
