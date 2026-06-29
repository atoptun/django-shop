# Generated manually to seed PaymentMethod instances

from django.db import migrations


def seed_payment_methods(apps, schema_editor):
    PaymentMethod = apps.get_model("orders", "PaymentMethod")
    PaymentMethod.objects.get_or_create(code="debit", name="Debit Card", is_active=True)
    PaymentMethod.objects.get_or_create(code="wallet", name="Digital Wallet", is_active=True)
    PaymentMethod.objects.get_or_create(code="cod", name="Cash On Delivery", is_active=True)


def reverse_seed_payment_methods(apps, schema_editor):
    PaymentMethod = apps.get_model("orders", "PaymentMethod")
    PaymentMethod.objects.filter(code__in=["debit", "wallet", "cod"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_paymentmethod_remove_payment_method_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_payment_methods, reverse_code=reverse_seed_payment_methods),
    ]
