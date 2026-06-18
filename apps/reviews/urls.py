from django.urls import path
from django.views.generic import TemplateView

app_name = "reviews"


urlpatterns = [
    path(
        "reviews/",
        TemplateView.as_view(template_name="reviews/review_list.html"),
        name="review_list",
    ),
]
