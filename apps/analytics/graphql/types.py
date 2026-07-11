import graphene


class DailyTrendType(graphene.ObjectType):
    date = graphene.Date(required=True)
    revenue = graphene.Decimal(required=True)
    count = graphene.Int(required=True)


class OrderAnalyticsType(graphene.ObjectType):
    revenue = graphene.Decimal(required=True)
    total_orders = graphene.Int(required=True)
    average_order_value = graphene.Decimal(required=True)
    trends = graphene.List(graphene.NonNull(DailyTrendType), required=True)


class ProductPopularityType(graphene.ObjectType):
    name = graphene.String(required=True)
    units_sold = graphene.Int(required=True)
    revenue = graphene.Decimal(required=True)


class ProductStockType(graphene.ObjectType):
    name = graphene.String(required=True)
    stock = graphene.Int(required=True)


class ProductAnalyticsType(graphene.ObjectType):
    popular_products = graphene.List(graphene.NonNull(ProductPopularityType), required=True)
    stock_levels = graphene.List(graphene.NonNull(ProductStockType), required=True)


class UserAnalyticsType(graphene.ObjectType):
    active_users_count = graphene.Int(required=True)
    repeat_purchase_rate = graphene.Float(required=True)
