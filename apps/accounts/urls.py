from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

app_name = "accounts"


urlpatterns = [
    # Web - auth
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="users/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "accounts/register/",
        TemplateView.as_view(template_name="accounts/register.html"),
        name="register",
    ),
    # Web - account
    path(
        "account/profile/",
        TemplateView.as_view(template_name="accounts/profile.html"),
        name="profile",
    ),
    path(
        "account/orders/",
        TemplateView.as_view(template_name="accounts/order_history.html"),
        name="order_history",
    ),
]
