from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    # Web - auth
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "accounts/register/",
        views.RegisterView.as_view(),
        name="register",
    ),
    # Web - account
    path(
        "account/profile/",
        views.ProfileView.as_view(),
        name="profile",
    ),
    path(
        "account/orders/",
        views.OrderHistoryView.as_view(),
        name="order_history",
    ),
    # Web - addresses
    path(
        "account/addresses/",
        views.AddressListView.as_view(),
        name="address_list",
    ),
    path(
        "account/addresses/add/",
        views.AddressCreateView.as_view(),
        name="address_add",
    ),
    path(
        "account/addresses/<int:pk>/edit/",
        views.AddressUpdateView.as_view(),
        name="address_edit",
    ),
    path(
        "account/addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),
    # Web - password reset
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
