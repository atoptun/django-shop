from typing import Any

from django import forms

from apps.accounts.models import Address
from apps.orders.models import PaymentMethod


class CheckoutForm(forms.Form):
    address_choice = forms.ChoiceField(required=False)
    full_name = forms.CharField(max_length=255, required=False)
    phone = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=100, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        empty_label="--- Select Payment Method ---",
        required=True,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_authenticated:
            choices: list[tuple[str, str]] = [("", "--- Select a saved address or enter below ---")]
            for addr in user.addresses.all():
                choices.append((str(addr.id), str(addr)))
            choices.append(("new", "Use a new address / Enter below"))
            self.fields["address_choice"].choices = choices  # type: ignore
        else:
            self.fields["address_choice"].choices = [("new", "Enter address details below")]  # type: ignore

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        address_choice: str = cleaned_data.get("address_choice", "")

        if not address_choice or address_choice == "new":
            fields_to_check: list[str] = ["full_name", "phone", "city", "address"]
            for field in fields_to_check:
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required when not using a saved address.")
        else:
            try:
                addr_id = int(address_choice)
                if self.user and not Address.objects.filter(id=addr_id, user=self.user).exists():
                    self.add_error(
                        "address_choice", "Selected address is invalid or does not belong to you."
                    )
            except ValueError:
                self.add_error("address_choice", "Invalid address selection.")

        return cleaned_data
