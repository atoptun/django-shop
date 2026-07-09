import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.api.tests import AuthClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client() -> AuthClient:
    client = AuthClient()

    user = UserFactory(email="testuser@example.com")
    user.profile.phone = "+380991234567"
    user.profile.city = "Kyiv"
    user.profile.address = "Test St 123"
    user.profile.save()

    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    client.user = user

    return client
