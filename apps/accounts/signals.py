from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

User = get_user_model()


@receiver(m2m_changed, sender=User.groups.through)  # type: ignore
def update_staff_status_on_group_change(sender, instance, action, pk_set, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        is_manager = instance.groups.filter(name="Managers").exists()
        if is_manager and not instance.is_staff:
            instance.is_staff = True
            instance.save(update_fields=["is_staff"])
        elif not is_manager and instance.is_staff and not instance.is_superuser:
            instance.is_staff = False
            instance.save(update_fields=["is_staff"])
