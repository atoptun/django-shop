from typing import Any

from django import template
from django.http import QueryDict

register = template.Library()


@register.simple_tag(takes_context=True)
def relative_url(context: dict[str, Any], field_name: str, value: int | str) -> str:
    """
    Generates a relative URL with the given query parameter and value,
    preserving existing query parameters.
    """
    request = context.get("request")
    if not request:
        return f"?{field_name}={value}"

    get_params: QueryDict = request.GET.copy()

    get_params[field_name] = str(value)

    return f"?{get_params.urlencode()}"
