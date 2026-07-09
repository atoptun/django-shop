from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views.products import CategoryAPIViewSet, ProductViewSet
from .views.users import (
    AddressViewSet,
    UserLoginView,
    UserProfileAPIView,
    UserRegisterAPIView,
    UserTokenRefreshView,
)

app_name = "api"

router = DefaultRouter()
router.register(r"users/addresses", AddressViewSet, basename="user-addresses")
router.register(r"categories", CategoryAPIViewSet, basename="categories")
router.register(r"products", ProductViewSet, basename="products")


urlpatterns = [
    path("", include(router.urls)),
    # OpenAPI Schema & Swagger Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="docs"),
    # JWT Auth and Registration
    path("users/register/", UserRegisterAPIView.as_view(), name="user-register"),
    path("users/login/", UserLoginView.as_view(), name="user-login"),
    path("users/token/refresh/", UserTokenRefreshView.as_view(), name="token-refresh"),
    # Profile
    path("users/me/", UserProfileAPIView.as_view(), name="user-detail"),
    # path("users/profile/", UserProfileAPIView.as_view(), name="user-profile"),
]
