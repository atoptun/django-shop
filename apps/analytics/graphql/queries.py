import graphene
from graphene import ResolveInfo

from apps.analytics.graphql.types import (
    DailyTrendType,
    OrderAnalyticsType,
    ProductAnalyticsType,
    ProductPopularityType,
    ProductStockType,
    UserAnalyticsType,
)
from apps.analytics.services import (
    OrderAnalyticsService,
    ProductAnalyticsService,
    UserAnalyticsService,
)


class Query(graphene.ObjectType):
    orders_analytics = graphene.Field(graphene.NonNull(OrderAnalyticsType))
    products_analytics = graphene.Field(
        graphene.NonNull(ProductAnalyticsType),
        popular_limit=graphene.Int(default_value=5),
    )
    users_analytics = graphene.Field(graphene.NonNull(UserAnalyticsType))

    def resolve_orders_analytics(self, info: ResolveInfo) -> OrderAnalyticsType:
        """Resolve order metrics and trends."""
        metrics = OrderAnalyticsService.get_order_metrics()
        return OrderAnalyticsType(
            revenue=metrics["revenue"],
            total_orders=metrics["total_orders"],
            average_order_value=metrics["average_order_value"],
            trends=[
                DailyTrendType(date=t["date"], revenue=t["revenue"], count=t["count"])
                for t in metrics["trends"]
            ],
        )

    def resolve_products_analytics(
        self, info: ResolveInfo, popular_limit: int
    ) -> ProductAnalyticsType:
        """Resolve product popularity and inventory stock levels."""
        metrics = ProductAnalyticsService.get_product_metrics(limit=popular_limit)
        return ProductAnalyticsType(
            popular_products=[
                ProductPopularityType(
                    name=p["name"],
                    units_sold=p["units_sold"],
                    revenue=p["revenue"],
                )
                for p in metrics["popular_products"]
            ],
            stock_levels=[
                ProductStockType(name=s["name"], stock=s["stock"]) for s in metrics["stock_levels"]
            ],
        )

    def resolve_users_analytics(self, info: ResolveInfo) -> UserAnalyticsType:
        """Resolve active users count and repeat purchase rates."""
        metrics = UserAnalyticsService.get_user_metrics()
        return UserAnalyticsType(
            active_users_count=metrics["active_users_count"],
            repeat_purchase_rate=metrics["repeat_purchase_rate"],
        )
