import graphene
from graphene import ResolveInfo

from apps.analytics.graphql.types import (
    OrderAnalyticsType,
    ProductAnalyticsType,
    UserAnalyticsType,
)
from apps.analytics.services import (
    OrderAnalyticsService,
    ProductAnalyticsService,
    UserAnalyticsService,
)


# Auth assumption: access control is enforced entirely by PrivateGraphQLView.dispatch().
# If schema.execute() is ever called directly (e.g. in scripts or tests outside the view),
# auth will be bypassed. Add graphene middleware or resolver-level guards if that changes.
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
            trends=metrics["trends"],
        )

    def resolve_products_analytics(
        self, info: ResolveInfo, popular_limit: int
    ) -> ProductAnalyticsType:
        """Resolve product popularity and inventory stock levels."""
        metrics = ProductAnalyticsService.get_product_metrics(limit=popular_limit)
        return ProductAnalyticsType(
            popular_products=metrics["popular_products"],
            stock_levels=metrics["stock_levels"],
        )

    def resolve_users_analytics(self, info: ResolveInfo) -> UserAnalyticsType:
        """Resolve active users count and repeat purchase rates."""
        metrics = UserAnalyticsService.get_user_metrics()
        return UserAnalyticsType(
            active_users_count=metrics["active_users_count"],
            repeat_purchase_rate=metrics["repeat_purchase_rate"],
        )
