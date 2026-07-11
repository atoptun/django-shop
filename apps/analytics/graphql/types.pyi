"""
Type stubs for apps/analytics/graphql/types.py.

Graphene's ObjectType metaclass dynamically maps class-level field descriptors
to __init__ kwargs at runtime, but pyright cannot see this. These stubs spell
out the constructor signatures explicitly so call sites in queries.py don't
need # type: ignore[call-arg] suppressions.

Keep in sync with types.py whenever fields are added/removed.
"""

import datetime
import decimal
from collections.abc import Sequence

class DailyTrendType:
    def __init__(
        self,
        date: datetime.date,
        revenue: decimal.Decimal,
        count: int,
    ) -> None: ...

class OrderAnalyticsType:
    def __init__(
        self,
        revenue: decimal.Decimal,
        total_orders: int,
        average_order_value: decimal.Decimal,
        trends: Sequence[DailyTrendType],
    ) -> None: ...

class ProductPopularityType:
    def __init__(
        self,
        name: str,
        units_sold: int,
        revenue: decimal.Decimal,
    ) -> None: ...

class ProductStockType:
    def __init__(
        self,
        name: str,
        stock: int,
    ) -> None: ...

class ProductAnalyticsType:
    def __init__(
        self,
        popular_products: Sequence[ProductPopularityType],
        stock_levels: Sequence[ProductStockType],
    ) -> None: ...

class UserAnalyticsType:
    def __init__(
        self,
        active_users_count: int,
        repeat_purchase_rate: float,
    ) -> None: ...
