# Generated manually to safely add a unique UUID field to existing rows.
# Reference: https://docs.djangoproject.com/en/6.0/howto/writing-migrations/#migrations-that-add-unique-fields

import uuid

from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for row in Order.objects.all():
        row.uuid = uuid.uuid4()
        row.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_delete_payment_delete_paymentmethod"),
    ]

    operations = [
        # Step 1: Add field as nullable
        migrations.AddField(
            model_name="order",
            name="uuid",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, null=True),
        ),
        # Step 2: Generate unique UUIDs for existing rows
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop, elidable=True),
        # Step 3: Alter field to be unique and non-nullable
        migrations.AlterField(
            model_name="order",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True, null=False
            ),
        ),
    ]
