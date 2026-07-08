from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0007_order_uuid"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.AlterModelTable(
                    name="Cart",
                    table="cart_cart",
                ),
                migrations.AlterModelTable(
                    name="CartItem",
                    table="cart_cartitem",
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="cart",
                    name="user",
                ),
                migrations.RemoveConstraint(
                    model_name="cartitem",
                    name="unique_cart_product",
                ),
                migrations.RemoveField(
                    model_name="cartitem",
                    name="cart",
                ),
                migrations.RemoveField(
                    model_name="cartitem",
                    name="product",
                ),
                migrations.DeleteModel(
                    name="Cart",
                ),
                migrations.DeleteModel(
                    name="CartItem",
                ),
            ],
        )
    ]
