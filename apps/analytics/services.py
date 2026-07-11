from datetime import date
from decimal import Decimal
from typing import TypedDict

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import TruncDate

from apps.orders.models import Order, OrderItem
from apps.products.models import Product

User = get_user_model()


def _or_zero_decimal(value: Decimal | None) -> Decimal:
    """Return value if not None, else Decimal('0.00')."""
    return value if value is not None else Decimal("0.00")


def _or_zero_int(value: int | None) -> int:
    """Return value if not None, else 0."""
    return value if value is not None else 0


class DailyTrendData(TypedDict):
    date: date
    revenue: Decimal
    count: int


class OrderAnalyticsData(TypedDict):
    revenue: Decimal
    total_orders: int
    average_order_value: Decimal
    trends: list[DailyTrendData]


class PopularProductData(TypedDict):
    name: str
    units_sold: int
    revenue: Decimal


class ProductStockData(TypedDict):
    name: str
    stock: int


class ProductAnalyticsData(TypedDict):
    popular_products: list[PopularProductData]
    stock_levels: list[ProductStockData]


class UserAnalyticsData(TypedDict):
    active_users_count: int
    repeat_purchase_rate: float


class OrderAnalyticsService:
    @staticmethod
    def get_order_metrics() -> OrderAnalyticsData:
        """Fetch general order metrics and daily trends using database aggregation."""
        paid_orders = Order.objects.filter(status=Order.Status.PAID)
        aggregates = paid_orders.aggregate(
            revenue=Sum("total_price"),
            total_orders=Count("id"),
            avg_value=Avg("total_price"),
        )

        revenue = _or_zero_decimal(aggregates["revenue"])
        total_orders = _or_zero_int(aggregates["total_orders"])
        avg_value = _or_zero_decimal(aggregates["avg_value"])

        trends_qs = (
            paid_orders.annotate(date_val=TruncDate("created_at"))
            .values("date_val")
            .annotate(day_revenue=Sum("total_price"), day_count=Count("id"))
            .order_by("date_val")
        )

        trends: list[DailyTrendData] = [
            {
                "date": t["date_val"],
                "revenue": _or_zero_decimal(t["day_revenue"]),
                "count": _or_zero_int(t["day_count"]),
            }
            for t in trends_qs
        ]

        return {
            "revenue": revenue,
            "total_orders": total_orders,
            "average_order_value": avg_value,
            "trends": trends,
        }


class ProductAnalyticsService:
    @staticmethod
    def get_product_metrics(limit: int = 5) -> ProductAnalyticsData:
        """Fetch lists of popular products and current inventory levels."""
        popular_qs = (
            OrderItem.objects.filter(order__status=Order.Status.PAID)
            .values("product__name")
            .annotate(
                units_sold_val=Sum("quantity"),
                revenue_val=Sum(F("quantity") * F("price")),
            )
            .order_by("-units_sold_val")[:limit]
        )

        popular_products: list[PopularProductData] = [
            {
                "name": p["product__name"],
                "units_sold": _or_zero_int(p["units_sold_val"]),
                "revenue": _or_zero_decimal(p["revenue_val"]),
            }
            for p in popular_qs
        ]

        stock_qs = Product.objects.all().values("name", "stock").order_by("stock")[:limit]
        stock_levels: list[ProductStockData] = [
            {
                "name": s["name"],
                "stock": _or_zero_int(s["stock"]),
            }
            for s in stock_qs
        ]

        return {
            "popular_products": popular_products,
            "stock_levels": stock_levels,
        }


class UserAnalyticsService:
    @staticmethod
    def get_user_metrics() -> UserAnalyticsData:
        """Compute user count metrics and repeat purchase rate."""
        active_users_count = (
            Order.objects.filter(status=Order.Status.PAID).values("user").distinct().count()
        )

        user_order_counts = (
            Order.objects.filter(status=Order.Status.PAID)
            .values("user")
            .annotate(order_count=Count("id"))
        )

        counts = list(user_order_counts)
        total_buyers = len(counts)
        repeat_buyers = sum(1 for u in counts if u["order_count"] > 1)

        repeat_purchase_rate = (
            round((repeat_buyers / total_buyers * 100), 2) if total_buyers > 0 else 0.0
        )

        return {
            "active_users_count": active_users_count,
            "repeat_purchase_rate": repeat_purchase_rate,
        }
