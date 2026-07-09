import pytest
from django.urls import include, path
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient

# =============================================================================
# DUMMY VIEWSET & ROUTER SETUP FOR TESTING
# =============================================================================


class DummyViewSet(viewsets.ViewSet):
    # Correct Regex pattern
    @action(detail=False, methods=["get"], url_path=r"regex/(?P<num>\d+)")
    def regex_action(self, request, num=None):
        return Response({"source": "regex", "num": num})

    # Incorrect Path Converter pattern (matches literal characters)
    @action(detail=False, methods=["get"], url_path="converter/<int:num>")
    def converter_action(self, request, num=None):
        return Response({"source": "converter", "num": num})


router = DefaultRouter()
router.register(r"dummy", DummyViewSet, basename="dummy")

# Export urlpatterns at module level to use with @pytest.mark.urls
urlpatterns = [
    path("api/", include(router.urls)),
]


# =============================================================================
# TEST SCENARIOS
# =============================================================================


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.urls("apps.api.tests.test_cart_url")
def test_regex_url_matching_success(api_client):
    # Regex pattern: ^api/dummy/regex/(?P<num>\d+)/$
    # Requesting a number should succeed (200 OK)
    url = "/api/dummy/regex/42/"
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["source"] == "regex"
    assert res.data["num"] == "42"


@pytest.mark.urls("apps.api.tests.test_cart_url")
def test_converter_url_matching_fails_on_integer(api_client):
    # Regex pattern generated: ^api/dummy/converter/<int:num>/$
    # Requesting an actual integer (e.g. 42) fails (404 Not Found)
    url = "/api/dummy/converter/42/"
    res = api_client.get(url)
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.urls("apps.api.tests.test_cart_url")
def test_converter_url_matching_succeeds_on_literal_string(api_client):
    # Regex pattern generated: ^api/dummy/converter/<int:num>/$
    # Requesting the literal string "<int:num>" matches! (200 OK)
    # But "num" argument is None because there is no capture group!
    url = "/api/dummy/converter/<int:num>/"
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["source"] == "converter"
    assert res.data["num"] is None
