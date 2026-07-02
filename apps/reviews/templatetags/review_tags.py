from typing import Any

from django import template
from django.core.paginator import Paginator

from apps.reviews.services import ReviewService

register = template.Library()


@register.inclusion_tag("reviews/review_list.html", takes_context=True)
def render_reviews(context: dict[str, Any], product: Any) -> dict[str, Any]:
    """Renders the paginated review list for the given product."""
    request = context["request"]
    page_number = request.GET.get("page", 1)

    review_service = ReviewService(request)
    all_reviews = review_service.get_reviews_for_product(product)

    paginator = Paginator(all_reviews, 6)
    page_obj = paginator.get_page(page_number)

    return {
        "request": request,
        "reviews": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
