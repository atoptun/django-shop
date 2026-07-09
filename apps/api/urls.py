from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views.cart import CartViewSet
from .views.orders import OrderViewSet
from .views.products import CategoryAPIViewSet, ProductViewSet
from .views.reviews import ReviewViewSet
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
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="orders")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "products/<slug:slug>/reviews/",
        ReviewViewSet.as_view({"get": "list", "post": "create"}),
        name="product-reviews-list",
    ),
    path(
        "products/<slug:slug>/reviews/can-review/",
        ReviewViewSet.as_view({"get": "can_review"}),
        name="product-reviews-can-review",
    ),
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
