from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.dashboard.dashboard import get_dashboard_context


@staff_member_required
def admin_dashboard_view(request: HttpRequest) -> HttpResponse:
    """Renders the custom dashboard with full admin context."""
    context = admin.site.each_context(request)
    context = get_dashboard_context(request, context)
    return render(request, "admin/dashboard.html", context)
