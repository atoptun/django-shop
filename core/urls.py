from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", lambda request: HttpResponse("OK", content_type="text/plain")),
    path("", include("apps.accounts.urls", namespace="accounts")),
    path("", include("apps.orders.urls", namespace="orders")),
    path("", include("apps.products.urls")),
    path("", include("apps.reviews.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
