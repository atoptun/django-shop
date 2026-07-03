from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("payments/pay/<uuid:order_uuid>/", views.PaymentProcessingView.as_view(), name="pay"),
    path(
        "payments/webhook/<str:provider_name>/", views.PaymentWebhookView.as_view(), name="webhook"
    ),
]
