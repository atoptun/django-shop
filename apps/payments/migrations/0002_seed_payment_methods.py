# Generated manually to seed PaymentMethod instances

from django.db import migrations


def seed_payment_methods(apps, schema_editor):
    PaymentMethod = apps.get_model("payments", "PaymentMethod")
    PaymentMethod.objects.get_or_create(code="debit", name="Debit Card", is_active=True)
    PaymentMethod.objects.get_or_create(
        code="wallet", name="Digital Wallet / PayPal", is_active=True
    )
    PaymentMethod.objects.get_or_create(code="bank", name="Bank Transfer", is_active=True)
    PaymentMethod.objects.get_or_create(code="cod", name="Cash On Delivery", is_active=True)


def reverse_seed_payment_methods(apps, schema_editor):
    PaymentMethod = apps.get_model("payments", "PaymentMethod")
    PaymentMethod.objects.filter(code__in=["debit", "wallet", "bank", "cod"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_payment_methods, reverse_code=reverse_seed_payment_methods),
    ]
