from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"

    def ready(self) -> None:
        import apps.orders.signals  # noqa: F401
