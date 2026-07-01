from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.db.models import Count
from unfold.admin import TabularInline

from apps.accounts.models import Address, Profile, User
from apps.common.admin import BaseSafeDeleteUnfoldAdmin
from apps.orders.models import Order
from apps.reviews.models import Review


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


class OrderInline(TabularInline):
    model = Order
    extra = 0
    tab = True
    show_change_link = True
    can_add = False
    can_delete = False
    fields = ["id", "status", "total_price", "created_at"]
    readonly_fields = ["id", "status", "total_price", "created_at"]


class ReviewInline(TabularInline):
    model = Review
    extra = 0
    tab = True
    show_change_link = True
    can_add = False
    can_delete = False
    fields = ["product", "rating", "comment", "created_at"]
    readonly_fields = ["product", "rating", "comment", "created_at"]


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
class UserAdmin(BaseSafeDeleteUnfoldAdmin, BaseUserAdmin):
    list_display = [
        # "username",
        "email",
        "first_name",
        "last_name",
        "orders_count_display",
        "reviews_count_display",
        "is_staff",
        "is_active",
    ]

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        if not request.user.is_superuser:  # type: ignore
            list_display = [
                field for field in list_display if field not in ["is_staff", "is_superuser"]
            ]

        return list_display

    # Show counts of related objects in the list display
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _orders_count=Count("orders", distinct=True),
            _reviews_count=Count("reviews", distinct=True),
        )

    @admin.display(description="Orders", ordering="_orders_count")
    def orders_count_display(self, obj):
        return getattr(obj, "_orders_count", 0)

    @admin.display(description="Reviews", ordering="_reviews_count")
    def reviews_count_display(self, obj):
        return getattr(obj, "_reviews_count", 0)

    # Custom actions to mark users as active or inactive
    actions = ["mark_as_active", "mark_as_inactive"]

    @admin.action(description="Mark selected users as Active")
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users successfully marked as Active.")

    @admin.action(description="Mark selected users as Inactive")
    def mark_as_inactive(self, request, queryset):
        updated = queryset.exclude(is_superuser=True).exclude(is_staff=True).update(is_active=False)
        self.message_user(request, f"{updated} users successfully marked as Inactive.")

    # Filtering and searching
    list_filter = ["is_staff", "is_superuser", "is_active"]

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)

        if not request.user.is_superuser:  # type: ignore
            list_filter = [f for f in list_filter if f not in ["is_staff", "is_superuser"]]

        return list_filter

    search_fields = ["first_name", "last_name", "email"]
    ordering = ["-date_joined"]

    # Customizing the add form to use email instead of username
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

    # Inlines for related models
    inlines = [ProfileInline, AddressInline, OrderInline, ReviewInline]

    # Customizing the fieldsets based on user permissions
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
        (
            ("Important dates"),
            {"classes": ["collapse"], "fields": ("last_login", "date_joined", "deleted")},
        ),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if not request.user.is_superuser:  # type: ignore
            fieldsets = [fs for fs in fieldsets if fs[0] != "Permissions"]
            # Hide password field for non-superusers
            new_fieldsets = []
            for title, fields_dict in fieldsets:
                if "fields" in fields_dict:
                    new_fields = [f for f in fields_dict["fields"] if f != "password"]
                    new_fieldsets.append((title, {**fields_dict, "fields": tuple(new_fields)}))
                else:
                    new_fieldsets.append((title, fields_dict))
            fieldsets = new_fieldsets

        return fieldsets

    # Customizing readonly fields based on user permissions
    readonly_fields = ["last_login", "date_joined", "deleted"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if not request.user.is_superuser:  # type: ignore
            readonly_fields = list(readonly_fields) + [
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ]

        return readonly_fields
