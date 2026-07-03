from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from apps.dashboard.views import admin_dashboard_view

urlpatterns = [
    path("admin/dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("admin/", admin.site.urls),
    path("health/", lambda request: HttpResponse("OK", content_type="text/plain")),
    path("", include("apps.accounts.urls", namespace="accounts")),
    path("", include("apps.orders.urls", namespace="orders")),
    path("", include("apps.products.urls", namespace="products")),
    path("", include("apps.reviews.urls", namespace="reviews")),
    path("", include("apps.payments.urls", namespace="payments")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
