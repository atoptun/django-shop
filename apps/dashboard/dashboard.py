from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.http import HttpRequest
from django.utils import timezone

from apps.orders.models import Order

User = get_user_model()


def calculate_delta(current_val: float, previous_val: float) -> float:
    """Calculates the percentage change between current and previous values."""
    if previous_val == 0:
        return 100.0 if current_val > 0 else 0.0
    return round(((current_val - previous_val) / previous_val) * 100, 1)


def get_period_filters(period: str, now: datetime) -> tuple[Q, Q | None, str, datetime | None]:
    """Generates time filters and delta labels based on the selected period."""
    current_filter = Q()
    previous_filter = None
    delta_text = ""
    start_date = None

    if period == "day":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today_start
        current_filter = Q(created_at__gte=today_start)
        previous_filter = Q(
            created_at__gte=today_start - timedelta(days=1),
            created_at__lt=today_start,
        )
        delta_text = "from yesterday"
    elif period == "week":
        this_monday = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_date = this_monday
        current_filter = Q(created_at__gte=this_monday)
        previous_filter = Q(
            created_at__gte=this_monday - timedelta(weeks=1),
            created_at__lt=this_monday,
        )
        delta_text = "from previous week"
    elif period == "month":
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = this_month_start
        current_filter = Q(created_at__gte=this_month_start)

        if this_month_start.month == 1:
            prev_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
        else:
            prev_month_start = this_month_start.replace(month=this_month_start.month - 1)

        previous_filter = Q(
            created_at__gte=prev_month_start,
            created_at__lt=this_month_start,
        )
        delta_text = "from previous month"

    return current_filter, previous_filter, delta_text, start_date


def get_users_delta(period: str, now: datetime, start_date: datetime | None) -> float:
    """Calculates user signup delta compared to the previous period."""
    if not start_date or period == "all":
        return 0.0

    if period == "day":
        curr_signups = User.objects.filter(date_joined__gte=start_date).count()
        prev_signups = User.objects.filter(
            date_joined__gte=start_date - timedelta(days=1),
            date_joined__lt=start_date,
        ).count()
    elif period == "week":
        curr_signups = User.objects.filter(date_joined__gte=start_date).count()
        prev_signups = User.objects.filter(
            date_joined__gte=start_date - timedelta(weeks=1),
            date_joined__lt=start_date,
        ).count()
    else:  # month
        curr_signups = User.objects.filter(date_joined__gte=start_date).count()
        if start_date.month == 1:
            prev_month_start = start_date.replace(year=start_date.year - 1, month=12)
        else:
            prev_month_start = start_date.replace(month=start_date.month - 1)

        prev_signups = User.objects.filter(
            date_joined__gte=prev_month_start,
            date_joined__lt=start_date,
        ).count()

    return calculate_delta(curr_signups, prev_signups)


def get_dashboard_context(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Generates the context dictionary for the custom Unfold admin dashboard."""
    period = request.GET.get("period", "all")
    now = timezone.now()

    current_filter, previous_filter, delta_text, start_date = get_period_filters(period, now)

    sales_statuses = [Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED]

    # 1. Total Sales (Revenue)
    curr_sales = (
        Order.objects.filter(current_filter, status__in=sales_statuses).aggregate(
            total=Sum("total_price")
        )["total"]
        or 0.0
    )
    curr_sales = float(curr_sales)

    if previous_filter:
        prev_sales = (
            Order.objects.filter(previous_filter, status__in=sales_statuses).aggregate(
                total=Sum("total_price")
            )["total"]
            or 0.0
        )
        prev_sales = float(prev_sales)
        sales_delta = calculate_delta(curr_sales, prev_sales)
    else:
        sales_delta = 0.0

    # 2. Total Users & Signups
    total_users = User.objects.filter(is_active=True).count()
    users_delta = get_users_delta(period, now, start_date)

    # 3. Total Orders
    curr_orders = Order.objects.filter(current_filter).count()

    if previous_filter:
        prev_orders = Order.objects.filter(previous_filter).count()
        orders_delta = calculate_delta(curr_orders, prev_orders)
    else:
        orders_delta = 0.0

    # 4. Total Pending
    curr_pending = Order.objects.filter(current_filter, status=Order.Status.PENDING).count()

    if previous_filter:
        prev_pending = Order.objects.filter(previous_filter, status=Order.Status.PENDING).count()
        pending_delta = calculate_delta(curr_pending, prev_pending)
    else:
        pending_delta = 0.0

    context.update(
        {
            "title": "Dashboard",
            "total_sales": curr_sales,
            "sales_delta": sales_delta,
            "total_users": total_users,
            "users_delta": users_delta,
            "total_orders": curr_orders,
            "orders_delta": orders_delta,
            "total_pending": curr_pending,
            "pending_delta": pending_delta,
            "delta_text": delta_text,
            "current_period": period,
        }
    )
    return context
