from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter

from apps.accounts.models import Address, Profile, User
from apps.common.admin import BaseSafeDeleteUnfoldAdmin


class AddressInline(TabularInline):
    model = Address
    extra = 0
    tab = True
    fields = ["recipient_name", "phone", "city", "address_line", "is_default", "deleted"]
    readonly_fields = ["deleted"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name == "address_line" and formfield:
            formfield.widget.attrs.update(
                {"rows": 3, "style": "min-height: 38px; resize: vertical;"}
            )

        return formfield


class ProfileInline(TabularInline):
    model = Profile
    extra = 0
    tab = True
    can_add = False
    can_delete = False
    fields = ["phone"]
    # readonly_fields = ["created_at", "updated_at", "deleted"]


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if not cleaned_data:
            return None
        email = cleaned_data.get("email")
        if email:
            self.instance.username = email
            self.instance.email = email
            cleaned_data["username"] = email
        return cleaned_data


@admin.register(User)
class UserAdmin(BaseUserAdmin, BaseSafeDeleteUnfoldAdmin):
    list_display = [
        # "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "deleted",
    ]
    list_filter = ["is_staff", "is_superuser", ("is_active", ChoicesDropdownFilter)]
    search_fields = ["first_name", "last_name", "email"]
    ordering = ["-date_joined"]
    add_form = UserCreationForm

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    inlines = [ProfileInline, AddressInline]

    def instance_info_cards(self, instance):
        if not instance.pk:
            return []

        return [
            {
                "title": ("Orders Count"),
                "value": instance.orders.count() if hasattr(instance, "orders") else 0,
                "description": _("Total orders placed by this user"),
            },
            {
                "title": ("Reviews Left"),
                "value": instance.reviews.count() if hasattr(instance, "reviews") else 0,
                "description": _("Product reviews submitted"),
            },
            {
                "title": ("Account Status"),
                "value": "Active" if instance.is_active else "Banned/Inactive",
                "color": "green" if instance.is_active else "red",
            },
        ]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            ("Permissions"),
            {
                "classes": ["collapse"],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (("Important dates"), {"fields": ("last_login", "date_joined", "deleted")}),
    )

    readonly_fields = ["last_login", "date_joined", "deleted"]


# @admin.register(Profile)
# class ProfileAdmin(BaseSafeDeleteUnfoldAdmin):
#     list_display = ["user", "phone", "city", "created_at", "deleted"]
#     search_fields = ["user__username", "user__email", "phone", "city"]
#     list_filter = ["city"]

#     # inlines = [AddressInline]
#     readonly_fields = ["created_at", "updated_at", "deleted"]

#     fields = [
#         "user",
#         "phone",
#         "city",
#         "address",
#         (
#             "created_at",
#             "updated_at",
#             "deleted",
#         ),
#     ]


# @admin.register(Address)
# class AddressAdmin(BaseSafeDeleteUnfoldAdmin):
#     list_display = ["recipient_name", "user", "city", "is_default", "deleted"]
#     search_fields = ["recipient_name", "city", "user__username"]
#     list_filter = ["city", "is_default"]

#     fields = [
#         "user",
#         "recipient_name",
#         "phone",
#         "city",
#         "address_line",
#         "is_default",
#         "deleted",
#     ]
#     readonly_fields = ["deleted"]
