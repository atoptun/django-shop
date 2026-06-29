from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "product/<slug:slug>/review",
        views.AddReviewView.as_view(),
        name="add_review",
    ),
]
